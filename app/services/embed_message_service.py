from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime

from app.db.repositories.shop import ShopRepository

from ..db.repositories.embed_messages import EmbedMessageRepository
from ..db.repositories.guilds import GuildRepository
from ..models.embed_message import (
    EmbedMessageModel, EmbedMessageCreate, EmbedMessageUpdate, 
    EmbedMessageFilter, EmbedMessageListResponse, EmbedMessageAnalytics
)
from ..models.user import PaginationParams

class EmbedMessageService:
    def __init__(
        self, 
        embed_repository: EmbedMessageRepository,
        shop_repository: ShopRepository,
        guild_repository: GuildRepository
    ):
        self.embed_repository = embed_repository
        self.shop_repository = shop_repository
        self.guild_repository = guild_repository

    async def create_embed_message(self, embed_data: EmbedMessageCreate) -> EmbedMessageModel:
        """
        Create a new embed message
        """
        # Check if embed with this message ID already exists
        existing_embed = await self.embed_repository.get_by_message_id(embed_data.messageId)
        if existing_embed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Embed message with message ID {embed_data.messageId} already exists"
            )
        
        return await self.embed_repository.create(embed_data)

    async def get_embed_message(self, embed_id: str) -> EmbedMessageModel:
        """
        Get an embed message with related item and guild names
        """
        embed = await self.embed_repository.get_by_id(embed_id)
        if not embed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embed message with ID {embed_id} not found"
            )
        
        # Get item name
        item = await self.shop_repository.get_by_id(embed.itemId)
        if item:
            embed.itemName = item.name
        print("embed.guildId", embed.guildId)
        # Get guild name
        guild = await self.guild_repository.get_by_guild_id(embed.guildId)
        if guild:
            embed.guildName = guild.guildName
        
        return embed

    async def get_embed_by_message_id(self, message_id: str) -> EmbedMessageModel:
        """
        Get an embed message by Discord message ID
        """
        embed = await self.embed_repository.get_by_message_id(message_id)
        if not embed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embed message with message ID {message_id} not found"
            )
        return embed

    async def get_embeds_by_item(self, item_id: str, pagination: PaginationParams) -> EmbedMessageListResponse:
        """
        Get embed messages by item ID
        """
        embeds, total = await self.embed_repository.get_by_item_id(item_id, pagination)
        return EmbedMessageListResponse(total=total, embed_messages=embeds)

    async def get_embeds_by_guild(self, guild_id: str, pagination: PaginationParams) -> EmbedMessageListResponse:
        """
        Get embed messages by guild ID
        """
        embeds, total = await self.embed_repository.get_by_guild_id(guild_id, pagination)
        return EmbedMessageListResponse(total=total, embed_messages=embeds)

    async def update_embed_message(self, embed_id: str, embed_data: EmbedMessageUpdate) -> EmbedMessageModel:
        """
        Update an embed message
        """
        # Check if embed exists
        existing_embed = await self.embed_repository.get_by_id(embed_id)
        if not existing_embed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embed message with ID {embed_id} not found"
            )
        
        # If changing message ID, check if new ID conflicts with existing
        if embed_data.messageId and embed_data.messageId != existing_embed.messageId:
            message_exists = await self.embed_repository.get_by_message_id(embed_data.messageId)
            if message_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Embed message with message ID {embed_data.messageId} already exists"
                )
        
        # Perform update
        updated_embed = await self.embed_repository.update(embed_id, embed_data)
        return updated_embed

    async def delete_embed_message(self, embed_id: str) -> Dict[str, Any]:
        """
        Delete an embed message
        """
        # Check if embed exists
        existing_embed = await self.embed_repository.get_by_id(embed_id)
        if not existing_embed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embed message with ID {embed_id} not found"
            )
        
        # Perform deletion
        success = await self.embed_repository.delete(embed_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete embed message"
            )
        
        return {"message": f"Embed message with ID {embed_id} deleted successfully"}

    async def delete_embed_by_message_id(self, message_id: str) -> Dict[str, Any]:
        """
        Delete an embed message by Discord message ID
        """
        # Check if embed exists
        existing_embed = await self.embed_repository.get_by_message_id(message_id)
        if not existing_embed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embed message with message ID {message_id} not found"
            )
        
        # Perform deletion
        success = await self.embed_repository.delete_by_message_id(message_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete embed message"
            )
        
        return {"message": f"Embed message with message ID {message_id} deleted successfully"}

    async def get_embed_messages(
        self, 
        filter_params: EmbedMessageFilter,
        pagination: PaginationParams
    ) -> EmbedMessageListResponse:
        """
        Get embed messages with filters and pagination
        """
        embeds, total = await self.embed_repository.get_all_with_filters(filter_params, pagination)
        return EmbedMessageListResponse(total=total, embed_messages=embeds)
    
    async def get_analytics(self) -> EmbedMessageAnalytics:
        """
        Get embed message analytics
        """
        return await self.embed_repository.get_analytics()