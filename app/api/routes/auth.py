import secrets
import string
from urllib.parse import urlencode
from fastapi import Response, Request
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional
import httpx

from ...config import settings
from ...db.database import get_database
from ...models.user import UserCreate, UserModel
from ...db.repositories.users import UserRepository

router = APIRouter()

# Token model
class Token(BaseModel):
    access_token: str
    token_type: str

# Token data model
class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

DISCORD_CLIENT_ID = settings.DISCORD_CLIENT_ID
DISCORD_CLIENT_SECRET = settings.DISCORD_CLIENT_SECRET
DISCORD_REDIRECT_URI = settings.DISCORD_REDIRECT_URI
DISCORD_API_ENDPOINT = settings.DISCORD_API_ENDPOINT

"""
TODO: Implement authentication logic
"""
@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate admin user and return JWT token
    """
    # For demo purposes
    if form_data.username != "admin" or form_data.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": "admin"}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# OAuth2 Discord Login
@router.get("/discord")
async def discord_login():
    """
    Redirect to Discord OAuth authorization URL
    """
    # Generate state token to prevent CSRF
    state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    # Construct the Discord OAuth URL
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify guilds',
        'state': state
    }
    
    discord_auth_url = f"{DISCORD_API_ENDPOINT}/oauth2/authorize?{urlencode(params)}"

    """
    TODO: store the state in a cookie or session
    """
    
    return {"url": discord_auth_url, "state": state}

@router.get("/discord/callback", response_model=Token)
async def discord_callback(code: str, state: str, request: Request, db=Depends(get_database)):
    """
    Handle Discord OAuth callback
    """

    """
    TODO: validate the state against stored value
    """
    
    # Exchange code for access token
    token_data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(f"{DISCORD_API_ENDPOINT}/oauth2/token", data=token_data)
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to retrieve Discord token"
            )
        
        discord_token = token_response.json()
        discord_access_token = discord_token.get("access_token")
        discord_refresh_token = discord_token.get("refresh_token")
        expires_in = discord_token.get("expires_in", 604800)  # Default 7 days
        token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Get user data from Discord
        headers = {"Authorization": f"Bearer {discord_token['access_token']}"}
        user_response = await client.get(f"{DISCORD_API_ENDPOINT}/users/@me", headers=headers)
        
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to retrieve Discord user data"
            )
        
        discord_data = user_response.json()        
    
    # Get or create user in database
    user_repo = UserRepository(db)
    discord_id = discord_data["id"]
    user = await user_repo.get_by_discord_id(discord_id)

    if not user:
        # Create new user
        from ...models.user import Subscription, SocialLinks
        new_user = UserCreate(
            discordId=discord_id,
            discordUsername=discord_data.get("username", ""),
            discordUserAvatarURL=f"https://cdn.discordapp.com/avatars/{discord_id}/{discord_data.get('avatar')}.png" if discord_data.get('avatar') else None,
            hyperBlockPoints=0,
            status="active",
            subscription=Subscription(),
            socials=SocialLinks(),
            discord_access_token=discord_access_token,
            discord_refresh_token=discord_refresh_token,
            discord_token_expires_at=token_expires_at
        )
        
        user = await user_repo.create(new_user)
    else:
        # Update existing user with latest Discord info
        now = datetime.now()
        await user_repo.update(
            str(user.id), 
            {
                "discordUsername": discord_data.get("username", user.discordUsername),
                "discordUserAvatarURL": f"https://cdn.discordapp.com/avatars/{discord_id}/{discord_data.get('avatar')}.png" if discord_data.get('avatar') else user.discordUserAvatarURL,
                "lastActive": now,
                "updatedAt": now,
                "discord_access_token": discord_access_token,
                "discord_refresh_token": discord_refresh_token,
                "discord_token_expires_at": token_expires_at
            }
        )
    
    # Create JWT token for the user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "discord_id": discord_id,
            "role": "user"  # Regular user role
        },
        expires_delta=access_token_expires
    )
    
    # Convert user model to dict for response
    user_dict = user.model_dump(by_alias=True)

    print(user_dict)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_dict
    }

@router.get("/refresh", response_model=Token)
async def refresh_jwt_token(request: Request, db=Depends(get_database)):
    """
    Refresh only the application JWT token, not the Discord token.
    This is used when the JWT expires (after 30 minutes) but the Discord token is still valid.
    """
    # Get the expired JWT token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.replace("Bearer ", "")
    
    # Try to decode the expired token to get user info
    try:
        # First, check if token is actually expired
        try:
            # Try to decode with expiration check
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # If we get here, token is still valid, no need to refresh
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is still valid, no need to refresh"
            )
            
        except JWTError as e:
            # Check if the error is due to expiration
            if "expired" not in str(e).lower():
                # If it's another kind of error, token is invalid
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Token is expired, continue with refresh process
            pass
        # Allow expired tokens to be decoded for this specific endpoint
        # only using it to identify the user, not for authentication
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}  # Important: don't verify expiration
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token content",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if Discord token is still valid
        now = datetime.now()
        if not user.discord_token_expires_at or user.discord_token_expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Discord token expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "discord_id": user.discordId,
                "role": "user"
            },
            expires_delta=access_token_expires
        )
        
        # Update last active time
        await user_repo.update(
            str(user.id),
            {
                "lastActive": now,
                "updatedAt": now
            }
        )
        
        user_dict = user.model_dump(by_alias=True)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_dict
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
# Helper function to create JWT access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt