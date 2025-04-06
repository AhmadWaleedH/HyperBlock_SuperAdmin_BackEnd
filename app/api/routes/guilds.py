from fastapi import APIRouter, Depends, File, Query, Path, HTTPException, UploadFile, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models.guild import (
    GuildModel, GuildCreate, GuildTeamResponse, GuildTopUsersResponse, GuildUpdate, GuildFilter, 
    GuildListResponse
)
from ...models.user import PaginationParams, UserModel
from ...services.guild_service import GuildService
from ...db.repositories.guilds import GuildRepository
from ...db.database import get_database
from ..dependencies import get_current_admin, get_current_user

router = APIRouter()

async def get_guild_service(database = Depends(get_database)) -> GuildService:
    guild_repository = GuildRepository(database)
    return GuildService(guild_repository)

@router.post("/", response_model=GuildModel, status_code=status.HTTP_201_CREATED)
async def create_guild(
    guild_data: GuildCreate,
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Create a new guild
    """
    return await guild_service.create_guild(guild_data)

@router.get("/{guild_id}", response_model=GuildModel)
async def get_guild(
    guild_id: str = Path(..., title="The ID of the guild to get"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Get a guild by ID
    """
    return await guild_service.get_guild(guild_id)

@router.get("/discord/{discord_guild_id}", response_model=GuildModel)
async def get_guild_by_discord_id(
    discord_guild_id: str = Path(..., title="The Discord ID of the guild to get"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Get a guild by Discord Guild ID
    """
    return await guild_service.get_guild_by_discord_id(discord_guild_id)

@router.patch("/{guild_id}", response_model=GuildModel)
async def update_guild(
    guild_data: GuildUpdate,
    guild_id: str = Path(..., title="The ID of the guild to update"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Update a guild
    """
    return await guild_service.update_guild(guild_id, guild_data)

@router.delete("/{guild_id}")
async def delete_guild(
    guild_id: str = Path(..., title="The ID of the guild to delete"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Delete a guild
    """
    return await guild_service.delete_guild(guild_id)

@router.get("/", response_model=GuildListResponse)
async def list_guilds(
    subscription_tier: Optional[str] = Query(None, description="Filter by subscription tier"),
    category: Optional[str] = Query(None, description="Filter by category"),
    user_category: Optional[str] = Query(None, description="Filter by user category"),
    total_members_min: Optional[int] = Query(None, description="Filter by minimum total members"),
    total_members_max: Optional[int] = Query(None, description="Filter by maximum total members"),
    bot_enabled: Optional[bool] = Query(None, description="Filter by bot enabled status"),
    owner_discord_id: Optional[str] = Query(None, description="Filter by owner Discord ID"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    List guilds with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = GuildFilter(
        subscription_tier=subscription_tier,
        category=category,
        user_category=user_category,
        total_members_min=total_members_min,
        total_members_max=total_members_max,
        bot_enabled=bot_enabled,
        owner_discord_id=owner_discord_id,
        created_after=created_after,
        created_before=created_before
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await guild_service.get_guilds(filter_params, pagination)

@router.get("/search/", response_model=GuildListResponse)
async def search_guilds(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Search guilds by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await guild_service.search_guilds(query, pagination)

@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_guild_analytics(
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Get analytics summary for all guilds
    """
    return await guild_service.get_analytics()

@router.get("/{guild_id}/top-users", response_model=GuildTopUsersResponse)
async def get_guild_top_users(
    guild_id: str = Path(..., title="The ID of the guild"),
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Get top users of a guild ordered by points in descending order
    """
    try:
        # Check if the guild exists first
        await guild_service.get_guild_by_discord_id(guild_id)
    except HTTPException:
        try:
            # Try with MongoDB ID if Discord ID lookup fails
            await guild_service.get_guild(guild_id)
        except HTTPException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
    
    # Get top users for the guild
    return await guild_service.get_guild_top_users(guild_id, limit)

@router.get("/{guild_id}/team", response_model=GuildTeamResponse)
async def get_guild_team(
    guild_id: str = Path(..., title="The ID of the guild"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of team members to return"),
    guild_service: GuildService = Depends(get_guild_service)
):
    """
    Get the admin/owner team members of a guild
    
    - **guild_id**: ID of the guild (Discord guild ID or MongoDB ID)
    - **limit**: Maximum number of team members to return (default: 10, max: 100)
    """
    try:
        # Check if the guild exists first
        try:
            await guild_service.get_guild_by_discord_id(guild_id)
        except HTTPException:
            # Try with MongoDB ID if Discord ID lookup fails
            await guild_service.get_guild(guild_id)
        
        # Get team members for the guild
        return await guild_service.get_guild_team(guild_id, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in get_guild_team endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving guild team: {str(e)}"
        )

# --------------------------------------------------------------------------------
# Endpoint for uploading guild card images
# --------------------------------------------------------------------------------
async def get_guild_service(database = Depends(get_database)) -> GuildService:
    guild_repository = GuildRepository(database)
    return GuildService(guild_repository)

# Add the new endpoint for uploading guild card images
@router.post("/{guild_id}/card-image", response_model=GuildModel)
async def upload_guild_card_image(
    guild_id: str = Path(..., title="The ID of the guild"),
    file: UploadFile = File(...),
    guild_service: GuildService = Depends(get_guild_service),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Upload a card image for a guild
    """

    # Check for empty file uploads
    if file is None or not hasattr(file, 'content_type') or file.filename == '' or file.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided or file is empty"
        )
    
    # Get the guild to verify ownership/admin rights
    try:
        guild = await guild_service.get_guild_by_discord_id(guild_id)
    except Exception:
        guild = await guild_service.get_guild(guild_id)
    
    # Check if current user is the guild owner or an admin
    is_guild_owner = guild.ownerDiscordId == current_user.discordId
    is_guild_admin = any(
        membership.guildId == guild.guildId and membership.userType in ["admin", "owner"]
        for membership in current_user.serverMemberships
    )
    is_system_admin = current_user.userGlobalStatus == "admin"
    
    if not (is_guild_owner or is_guild_admin or is_system_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload card image for this guild"
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Max file size (2MB)
    max_size = 2 * 1024 * 1024
    file_size = 0
    
    # Calculate file size
    chunk = await file.read(1024)
    while chunk:
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 2MB"
            )
        chunk = await file.read(1024)
    
    # Reset file position
    await file.seek(0)
    
    # Upload guild card image
    return await guild_service.upload_guild_card_image(guild_id, file)
