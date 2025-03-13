import base64
import hashlib
import secrets
import string
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, status
from typing import Optional, List
from datetime import datetime, timedelta

from app.api.dependencies import get_current_admin, get_current_user

from ...models.user import (
    SocialAccounts, SocialLinks, TwitterAccount, UserModel, UserCreate, UserResponse, UserUpdate, UserFilter, 
    UserListResponse, PaginationParams
)
from ...services.user_service import UserService
from ...db.repositories.users import UserRepository
from ...db.database import get_database

router = APIRouter()

async def get_user_service(database = Depends(get_database)) -> UserService:
    user_repository = UserRepository(database)
    return UserService(user_repository)

@router.post("/", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user
    """
    return await user_service.create_user(user_data)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """
    Get the current logged-in user's information
    """
    return current_user

@router.get("/{user_id}", response_model=UserModel, dependencies=[Depends(get_current_user)])
async def get_user(
    user_id: str = Path(..., title="The ID of the user to get"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by ID
    """
    return await user_service.get_user(user_id)

@router.get("/discord/{discord_id}", response_model=UserModel)
async def get_user_by_discord_id(
    discord_id: str = Path(..., title="The Discord ID of the user to get"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by Discord ID
    """
    return await user_service.get_user_by_discord_id(discord_id)

@router.patch("/{user_id}", response_model=UserModel)
async def update_user(
    user_data: UserUpdate,
    user_id: str = Path(..., title="The ID of the user to update"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update a user
    """
    return await user_service.update_user(user_id, user_data)

@router.delete("/{user_id}", dependencies=[Depends(get_current_admin)])
async def delete_user(
    user_id: str = Path(..., title="The ID of the user to delete"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete a user
    """
    return await user_service.delete_user(user_id)

@router.get("/", response_model=UserListResponse, dependencies=[Depends(get_current_admin)])
async def list_users(
    subscription_tier: Optional[str] = Query(None, description="Filter by subscription tier"),
    userGlobalStatus: Optional[str] = Query(None, description="Filter by user status"),
    wallet_type: Optional[str] = Query(None, description="Filter by wallet type"),
    min_points: Optional[int] = Query(None, description="Minimum hyperblock points"),
    max_points: Optional[int] = Query(None, description="Maximum hyperblock points"),
    discord_username: Optional[str] = Query(None, description="Filter by Discord username"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    user_service: UserService = Depends(get_user_service)
):
    """
    List users with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = UserFilter(
        subscription_tier=subscription_tier,
        userGlobalStatus=userGlobalStatus,
        wallet_type=wallet_type,
        min_points=min_points,
        max_points=max_points,
        discord_username=discord_username,
        created_after=created_after,
        created_before=created_before
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await user_service.get_users(filter_params, pagination)

@router.get("/search/", response_model=UserListResponse)
async def search_users(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search users by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await user_service.search_users(query, pagination)

# ------------------------------------------------------------------------------------------
# Discord Guilds
# ------------------------------------------------------------------------------------------
from pydantic import BaseModel
import httpx
from ...config import settings

# Response Models
class GuildWithStatus(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    has_hyperblock_bot: bool
    permissions: Optional[int] = None
    features: Optional[List[str]] = None
    
class GuildsResponse(BaseModel):
    guilds: List[GuildWithStatus]

@router.get("/me/discord-guilds", response_model=GuildsResponse)
async def get_user_discord_guilds(
    current_user: UserModel = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Fetch user's Discord guilds where they are an admin 
    and indicate which ones have the Hyperblock bot installed
    """
    # Check if Discord token is still valid
    if not current_user.discord_access_token or not current_user.discord_token_expires_at or current_user.discord_token_expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Discord token expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create set of guild IDs where the user has HyperBlock bot
    hyperblock_guild_ids = {
        membership.guildId 
        for membership in current_user.serverMemberships 
        if membership.status == "active"
    }
    
    # Fetch guilds from Discord API
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {current_user.discord_access_token}"}
        response = await client.get(f"{settings.DISCORD_API_ENDPOINT}/users/@me/guilds", headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to retrieve guilds from Discord API",
            )
        
        guilds_data = response.json()
        
        # Filter guilds where user has admin permissions
        # The permission integer 0x8 (8) represents the ADMINISTRATOR permission
        admin_guilds = [
            guild for guild in guilds_data 
            if (int(guild.get("permissions", 0)) & 0x8) == 0x8
        ]
        
        # Map guilds to response format with hyperblock bot status
        guilds_with_status = [
            GuildWithStatus(
                id=guild["id"],
                name=guild["name"],
                icon=guild.get("icon"),
                has_hyperblock_bot=guild["id"] in hyperblock_guild_ids,
                permissions=int(guild.get("permissions", 0)),
                features=guild.get("features", [])
            ) 
            for guild in admin_guilds
        ]
        
        return GuildsResponse(guilds=guilds_with_status)
    
# ------------------------------------------------------------------------------------------
# Twitter Connect
# ------------------------------------------------------------------------------------------
class TwitterAuthResponse(BaseModel):
    auth_url: str
    state: str

class TwitterCallbackRequest(BaseModel):
    code: str
    state: str

class TwitterAccountResponse(BaseModel):
    connected: bool
    account: Optional[TwitterAccount] = None

# helper functions for PKCE
def generate_code_verifier(length=64):
    return ''.join(secrets.choice(string.ascii_letters + string.digits + '-._~') for _ in range(length))

def generate_code_challenge(verifier):
    hash_digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    b64_digest = base64.urlsafe_b64encode(hash_digest).decode('utf-8')
    return b64_digest.rstrip('=')

# Twitter Account Connection Endpoints
@router.get("/connect/twitter", response_model=TwitterAuthResponse)
async def connect_twitter_account(request: Request):
    """
    Generate Twitter OAuth URL for account connection
    """

    # Generate state token to prevent CSRF
    state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

    # Generate PKCE code verifier and challenge
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Store code_verifier in session for later use
    request.session["twitter_code_verifier"] = code_verifier
    request.session["twitter_state"] = state
    
    """
    TODO: Update State token from session storage to redis or database
    """
    
    # Construct the Twitter OAuth URL
    params = {
        'response_type': 'code',
        'client_id': settings.TWITTER_CLIENT_ID,
        'redirect_uri': settings.TWITTER_REDIRECT_URI,
        'scope': 'tweet.read users.read offline.access',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    
    auth_url = f"{settings.TWITTER_AUTH_URL}?{urlencode(params)}"
    
    return TwitterAuthResponse(auth_url=auth_url, state=state)

@router.get("/connect/twitter/callback", response_model=TwitterAccountResponse)
async def twitter_callback(
    code: str,
    state: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Handle Twitter OAuth callback and connect account to user profile
    """
    # Verify state to prevent CSRF
    stored_state = request.session.get("twitter_state")
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state parameter. Expected: {stored_state}, Got: {state}"
        )
    
    # Get stored code_verifier
    code_verifier = request.session.get("twitter_code_verifier")
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code verifier"
        )
    
    # Exchange code for access token
    token_data = {
        'client_id': settings.TWITTER_CLIENT_ID,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.TWITTER_REDIRECT_URI,
        'code_verifier': code_verifier
    }
        
    try:
        async with httpx.AsyncClient() as client:
            # Create Basic auth header with client credentials
            auth_credentials = f"{settings.TWITTER_CLIENT_ID}:{settings.TWITTER_CLIENT_SECRET}"
            encoded_credentials = base64.b64encode(auth_credentials.encode()).decode()
            
            # Get Twitter access token
            token_response = await client.post(
                settings.TWITTER_TOKEN_URL, 
                data=token_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {encoded_credentials}"
                }
            )
            
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to retrieve Twitter token: {token_response.text}"
                )
            
            token_data = token_response.json()
            token_type = token_data.get("token_type")
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 7200)

            token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            
            # Get Twitter user data
            user_response = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={
                    "user.fields": "profile_image_url,username,id,name"
                }
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to retrieve Twitter user data: {user_response.text}"
                )
            
            twitter_data = user_response.json().get("data", {})
            
            # Construct Twitter account data
            twitter_account = TwitterAccount(
                id=twitter_data.get("id"),
                username=twitter_data.get("username"),
                profileUrl=twitter_data.get("profile_image_url"),
                tokenType=token_type,
                accessToken=access_token,
                refreshToken=refresh_token,
                tokenExpiresAt = token_expires_at
            )
            
            # Create or update social accounts object
            social_accounts = current_user.socialAccounts or SocialAccounts()
            social_accounts.twitter = twitter_account
            
            # Update user profile
            update_data = UserUpdate(
                socialAccounts=social_accounts,
                lastActive=datetime.now()
            )

            # If user doesn't have X/Twitter in socials, add it
            if not current_user.socials.x and twitter_account.username:
                current_user.socials.x = f"https://twitter.com/{twitter_account.username}"
                update_data.socials = current_user.socials
            
            # Update the user
            updated_user = await user_service.update_user(str(current_user.id), update_data)
            
            return TwitterAccountResponse(
                connected=True,
                account=twitter_account
            )
            
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error connecting Twitter account: {str(e)}"
        )

@router.delete("/connect/twitter", response_model=TwitterAccountResponse)
async def disconnect_twitter_account(
    current_user: UserModel = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Disconnect Twitter account from user profile
    """
    # Create new social accounts without Twitter
    social_accounts = current_user.socialAccounts or SocialAccounts()
    social_accounts.twitter = None
    
    # Update socials if needed (remove Twitter URL)
    socials = current_user.socials
    socials.x = None
    
    # Update the user
    update_data = UserUpdate(
        socialAccounts=social_accounts,
        socials=socials,
        lastActive=datetime.now()
    )
    
    await user_service.update_user(str(current_user.id), update_data)
    
    return TwitterAccountResponse(connected=False)