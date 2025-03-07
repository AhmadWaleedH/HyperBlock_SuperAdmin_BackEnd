from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List, Dict, Any

from app.db.repositories.guilds import GuildRepository
from app.db.repositories.shop import ShopRepository

from ...models.embed_message import (
    EmbedMessageModel, EmbedMessageCreate, EmbedMessageUpdate, 
    EmbedMessageFilter, EmbedMessageListResponse, EmbedMessageAnalytics
)
from ...models.user import PaginationParams
from ...services.embed_message_service import EmbedMessageService
from ...db.repositories.embed_messages import EmbedMessageRepository
from ...db.database import get_database
from ..dependencies import get_current_admin

router = APIRouter()

async def get_embed_service(database = Depends(get_database)) -> EmbedMessageService:
    embed_repository = EmbedMessageRepository(database)
    shop_repository = ShopRepository(database)
    guild_repository = GuildRepository(database)
    
    return EmbedMessageService(
        embed_repository=embed_repository,
        shop_repository=shop_repository,
        guild_repository=guild_repository
    )

@router.post("/", response_model=EmbedMessageModel, status_code=status.HTTP_201_CREATED)
async def create_embed_message(
    embed_data: EmbedMessageCreate,
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Create a new embed message
    """
    return await embed_service.create_embed_message(embed_data)

@router.get("/{embed_id}", response_model=EmbedMessageModel)
async def get_embed_message(
    embed_id: str = Path(..., title="The ID of the embed message to get"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Get an embed message by ID
    """
    return await embed_service.get_embed_message(embed_id)

@router.get("/message/{message_id}", response_model=EmbedMessageModel)
async def get_embed_by_message_id(
    message_id: str = Path(..., title="The Discord message ID of the embed to get"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Get an embed message by Discord message ID
    """
    return await embed_service.get_embed_by_message_id(message_id)

@router.get("/item/{item_id}", response_model=EmbedMessageListResponse)
async def get_embeds_by_item(
    item_id: str = Path(..., title="The item ID to get embeds for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Get embed messages by item ID
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await embed_service.get_embeds_by_item(item_id, pagination)

@router.get("/guild/{guild_id}", response_model=EmbedMessageListResponse)
async def get_embeds_by_guild(
    guild_id: str = Path(..., title="The guild ID to get embeds for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Get embed messages by guild ID
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await embed_service.get_embeds_by_guild(guild_id, pagination)

@router.patch("/{embed_id}", response_model=EmbedMessageModel)
async def update_embed_message(
    embed_data: EmbedMessageUpdate,
    embed_id: str = Path(..., title="The ID of the embed message to update"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Update an embed message
    """
    return await embed_service.update_embed_message(embed_id, embed_data)

@router.delete("/{embed_id}")
async def delete_embed_message(
    embed_id: str = Path(..., title="The ID of the embed message to delete"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Delete an embed message
    """
    return await embed_service.delete_embed_message(embed_id)

@router.delete("/message/{message_id}")
async def delete_embed_by_message_id(
    message_id: str = Path(..., title="The Discord message ID of the embed to delete"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Delete an embed message by Discord message ID
    """
    return await embed_service.delete_embed_by_message_id(message_id)

@router.get("/", response_model=EmbedMessageListResponse)
async def list_embed_messages(
    guildId: Optional[str] = Query(None, description="Filter by guild ID"),
    channelId: Optional[str] = Query(None, description="Filter by channel ID"),
    itemId: Optional[str] = Query(None, description="Filter by item ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    List embed messages with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = EmbedMessageFilter(
        guildId=guildId,
        channelId=channelId,
        itemId=itemId
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await embed_service.get_embed_messages(filter_params, pagination)

@router.get("/analytics/summary", response_model=EmbedMessageAnalytics)
async def get_embed_analytics(
    embed_service: EmbedMessageService = Depends(get_embed_service)
):
    """
    Get analytics summary for embed messages
    """
    return await embed_service.get_analytics()