import base64
import hashlib
import secrets
import string
from urllib.parse import urlencode
from fastapi import APIRouter, Body, Depends, File, Query, Path, HTTPException, Request, UploadFile, status
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta

from app.api.dependencies import get_current_admin, get_current_user
from app.db.repositories.guilds import GuildRepository

from ...models.user import (
    PointsExchangeRequest, PointsExchangeResponse, SocialAccounts, SocialLinks, TwitterAccount, UserModel, UserCreate, UserResponse, UserUpdate, UserFilter, 
    UserListResponse, PaginationParams
)
from ...services.user_service import UserService
from ...db.repositories.users import UserRepository
from ...db.database import get_database

router = APIRouter()

async def get_user_service(database = Depends(get_database)) -> UserService:
    user_repository = UserRepository(database)
    guild_repository = GuildRepository(database)
    return UserService(user_repository, guild_repository)

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
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):    
    """
    Get the current logged-in user's information
    """
    return await user_service.enrich_user_with_guild_info(current_user)

@router.get("/{user_id}", response_model=UserModel, dependencies=[Depends(get_current_user)])
async def get_user(
    user_id: str = Path(..., title="The ID of the user to get"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by ID
    """
    user = await user_service.get_user(user_id)
    return await user_service.enrich_user_with_guild_info(user)

@router.get("/discord/{discord_id}", response_model=UserModel)
async def get_user_by_discord_id(
    discord_id: str = Path(..., title="The Discord ID of the user to get"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by Discord ID
    """
    user = await user_service.get_user_by_discord_id(discord_id)
    return await user_service.enrich_user_with_guild_info(user)

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

@router.post("/exchange-points", response_model=PointsExchangeResponse)
async def exchange_guild_points(
    exchange_data: PointsExchangeRequest,
    current_user: UserModel = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Exchange guild points for global HyperBlock points
    """
    return await user_service.exchange_guild_points_to_global(
        str(current_user.id), 
        exchange_data.guild_id, 
        exchange_data.points_amount
    )

# ------------------------------------------------------------------------------------------
# Discord Guilds
# ------------------------------------------------------------------------------------------
from pydantic import BaseModel, Field
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

# ------------------------------------------------------------------------------------------
# Card Image Upload
# ------------------------------------------------------------------------------------------
@router.post("/{user_id}/card-image", response_model=UserModel)
async def upload_card_image(
    user_id: str = Path(..., title="The ID of the user"),
    file: UploadFile = File(...),
    user_service: UserService = Depends(get_user_service),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Upload a card image for a user
    """
    
    # Check for empty file uploads
    if file is None or not hasattr(file, 'content_type') or file.filename == '' or file.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided or file is empty"
        )
    
    # Check if current user matches user_id
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload card image for this user"
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Max file size (5MB)
    max_size = 5 * 1024 * 1024
    file_size = 0
    
    # Calculate file size
    chunk = await file.read(1024)
    while chunk:
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 5MB"
            )
        chunk = await file.read(1024)
    
    # Reset file position
    await file.seek(0)
    
    # Upload card image
    return await user_service.upload_card_image(user_id, file)


# ------------------------------------------------------------------------------------------
# Blockchain Transaction Lookup
# ------------------------------------------------------------------------------------------

# Model for the request
class TransactionRequest(BaseModel):
    chain: str = Field(..., description="Blockchain network (bsc, ethereum, polygon, solana, tron)")
    txHash: str = Field(..., description="Transaction hash to lookup")

# Model for the response
class TransactionResponse(BaseModel):
    data: Dict[str, Any]

# RPC endpoints
# Updated RPC endpoints with fallbacks
RPC_ENDPOINTS = {
    # Ethereum nodes
    "ethereum": [
        "https://eth.llamarpc.com",
        "https://eth.drpc.org",
        "https://ethereum.publicnode.com"
    ],
    # BSC nodes
    "bsc": [
        "https://bsc-dataseed.binance.org/",
        "https://bsc-dataseed1.defibit.io/",
        "https://bsc-dataseed1.ninicoin.io/"
    ],
    # Polygon nodes
    "polygon": [
        "https://polygon-rpc.com/",
        "https://polygon.llamarpc.com",
        "https://polygon-mainnet.public.blastapi.io"
    ],
    # Solana nodes
    "solana": [
        "https://api.mainnet-beta.solana.com",
        "https://solana-mainnet.g.alchemy.com/v2/demo",
        "https://rpc.ankr.com/solana"
    ],
    # Tron endpoints
    "tron": [
        "https://api.trongrid.io",
        "https://apilist.tronscan.org"
    ],
    # Block explorers for fallback
    "explorers": {
        "ethereum": "https://api.etherscan.io/api",
        "bsc": "https://api.bscscan.com/api",
        "polygon": "https://api.polygonscan.com/api",
        "solana": "https://public-api.solscan.io/transaction",
        "tron": "https://apilist.tronscan.org/api/transaction-info"
    }
}

@router.post("/get-transaction", response_model=TransactionResponse)
async def get_transaction(request: TransactionRequest = Body(...)):
    """
    Fetch transaction details from various blockchains
    """
    chain = request.chain.lower()
    tx_hash = request.txHash
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # EVM-compatible chains (Ethereum, BSC, Polygon)
            if chain in ["ethereum", "bsc", "polygon"]:
                # Try each RPC endpoint until one works
                for endpoint in RPC_ENDPOINTS[chain]:
                    try:
                        payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "eth_getTransactionByHash",
                            "params": [tx_hash]
                        }
                        response = await client.post(endpoint, json=payload, timeout=5.0)
                        if response.status_code == 200:
                            result = response.json()
                            # Check if we got a valid result
                            if "result" in result and result["result"]:
                                return {"data": result}
                    except (httpx.RequestError, httpx.TimeoutException):
                        continue
                
                # If all RPC endpoints fail, try the explorer API as fallback
                try:
                    explorer_url = RPC_ENDPOINTS["explorers"][chain]
                    response = await client.get(f"{explorer_url}?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}", timeout=5.0)
                    if response.status_code == 200:
                        result = response.json()
                        if "result" in result and result["result"]:
                            return {"data": result}
                except Exception:
                    pass
                
                # If everything fails
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transaction not found on {chain} network: {tx_hash}"
                )
                
            # Solana chain
            elif chain == "solana":
                # Try each Solana RPC endpoint
                for endpoint in RPC_ENDPOINTS["solana"]:
                    try:
                        payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getTransaction",
                            "params": [tx_hash, "json"]
                        }
                        response = await client.post(endpoint, json=payload, timeout=5.0)
                        if response.status_code == 200:
                            result = response.json()
                            if "result" in result and result["result"]:
                                return {"data": result}
                    except (httpx.RequestError, httpx.TimeoutException):
                        continue
                
                # Try Solscan API as fallback
                try:
                    response = await client.get(f"{RPC_ENDPOINTS['explorers']['solana']}/{tx_hash}", timeout=5.0)
                    if response.status_code == 200:
                        return {"data": response.json()}
                except Exception:
                    pass
                
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transaction not found on Solana network: {tx_hash}"
                )
                
            # Tron chain
            elif chain == "tron":
                # Try Tron Node API first
                try:
                    response = await client.post(f"{RPC_ENDPOINTS['tron'][0]}/wallet/gettransactionbyid", json={
                        "value": tx_hash
                    }, timeout=5.0)
                    
                    if response.status_code == 200 and response.json():
                        return {"data": response.json()}
                except Exception:
                    pass
                
                # Then try the v1 API format
                try:
                    response = await client.get(f"{RPC_ENDPOINTS['tron'][0]}/v1/transactions/{tx_hash}", timeout=5.0)
                    if response.status_code == 200:
                        return {"data": response.json()}
                except Exception:
                    pass
                
                # Finally try Tronscan API
                try:
                    response = await client.get(f"{RPC_ENDPOINTS['tron'][1]}/api/transaction-info?hash={tx_hash}", timeout=5.0)
                    if response.status_code == 200:
                        return {"data": response.json()}
                except Exception:
                    pass
                
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transaction not found on Tron network: {tx_hash}"
                )
                
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported blockchain: {chain}"
                )
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to blockchain RPC: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred: {str(e)}"
            )       
