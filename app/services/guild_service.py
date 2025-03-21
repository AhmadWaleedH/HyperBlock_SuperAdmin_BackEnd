from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, UploadFile, status
from datetime import datetime

from app.services.s3_service import S3Service

from ..db.repositories.guilds import GuildRepository
from ..models.guild import GuildModel, GuildCreate, GuildUpdate, GuildFilter, GuildListResponse
from ..models.user import PaginationParams

class GuildService:
    def __init__(self, guild_repository: GuildRepository):
        self.guild_repository = guild_repository

    async def create_guild(self, guild_data: GuildCreate) -> GuildModel:
        """
        Create a new guild
        """
        # Check if guild with the Discord guild ID already exists
        existing_guild = await self.guild_repository.get_by_guild_id(guild_data.guildId)
        if existing_guild:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Guild with Discord ID {guild_data.guildId} already exists"
            )
        
        return await self.guild_repository.create(guild_data)

    async def get_guild(self, guild_id: str) -> GuildModel:
        """
        Get a guild by ID
        """
        guild = await self.guild_repository.get_by_id(guild_id)
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        return guild

    async def get_guild_by_discord_id(self, discord_guild_id: str) -> GuildModel:
        """
        Get a guild by Discord Guild ID
        """
        guild = await self.guild_repository.get_by_guild_id(discord_guild_id)
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with Discord ID {discord_guild_id} not found"
            )
        return guild

    async def update_guild(self, guild_id: str, guild_data: GuildUpdate) -> GuildModel:
        """
        Update a guild
        """
        # Check if guild exists
        existing_guild = await self.guild_repository.get_by_id(guild_id)
        if not existing_guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Perform update
        updated_guild = await self.guild_repository.update(guild_id, guild_data)
        return updated_guild

    async def delete_guild(self, guild_id: str) -> Dict[str, Any]:
        """
        Delete a guild
        """
        # Check if guild exists
        existing_guild = await self.guild_repository.get_by_id(guild_id)
        if not existing_guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Perform deletion
        success = await self.guild_repository.delete(guild_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete guild"
            )
        
        return {"message": f"Guild with ID {guild_id} deleted successfully"}

    async def get_guilds(
        self, 
        filter_params: GuildFilter,
        pagination: PaginationParams
    ) -> GuildListResponse:
        """
        Get guilds with filters and pagination
        """
        guilds, total = await self.guild_repository.get_all_with_filters(filter_params, pagination)
        return GuildListResponse(total=total, guilds=guilds)

    async def search_guilds(
        self, 
        query: str,
        pagination: PaginationParams
    ) -> GuildListResponse:
        """
        Search guilds by a query string
        """
        guilds, total = await self.guild_repository.search(query, pagination)
        return GuildListResponse(total=total, guilds=guilds)
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get guild analytics
        """
        return await self.guild_repository.get_guild_analytics()
    
    async def upload_guild_card_image(self, guild_id: str, file: UploadFile) -> GuildModel:
        """
        Upload a card image for a guild and update its profile
        """
        # Check if guild exists
        existing_guild = await self.guild_repository.get_by_id(guild_id)
        if not existing_guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Upload file to S3
        s3_service = S3Service()
        
        # If guild already has a card image, delete it first
        if existing_guild.guildCardImageURL:
            await s3_service.delete_file(existing_guild.guildCardImageURL)
        
        # Upload new image
        card_image_url = await s3_service.upload_file(
            file, 
            folder=f"guild-cards/{guild_id}"
        )
        
        # Update guild with new card image URL
        guild_update = GuildUpdate(guildCardImageURL=card_image_url, updatedAt=datetime.now())
        return await self.guild_repository.update(guild_id, guild_update)