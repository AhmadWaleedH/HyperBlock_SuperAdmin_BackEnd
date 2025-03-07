from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models.guild import (
    GuildModel, GuildCreate, GuildUpdate, GuildFilter, 
    GuildListResponse
)
from ...models.user import PaginationParams
from ...services.guild_service import GuildService
from ...db.repositories.guilds import GuildRepository
from ...db.database import get_database
from ..dependencies import get_current_admin

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
    rating: Optional[str] = Query(None, description="Filter by analytics rating"),
    is_top10: Optional[bool] = Query(None, description="Filter by top 10 status"),
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
        rating=rating,
        is_top10=is_top10,
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