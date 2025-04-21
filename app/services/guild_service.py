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
    
    async def get_guild_top_users(
        self, 
        guild_id: str,
        limit: int
    ) -> Dict[str, Any]:
        """
        Get top users of a guild ordered by points in descending order
        """
        # Delegate to the repository
        try:
            # Delegate to the repository
            users_data, total = await self.guild_repository.get_guild_top_users(guild_id, limit)
            
            # Transform the data to match our response model
            user_points = []
            for user in users_data:
                user_points.append({
                    "discordId": user["discordId"],
                    "discordUsername": user["discordUsername"],
                    "guildId": user["guildId"],
                    "points": user["points"]
                })
            
            return {
                "total": total,
                "users": user_points
            }
        except Exception as e:
            print(f"Error in guild_service.get_guild_top_users: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving top users: {str(e)}"
            )
        
    async def get_guild_team(
        self, 
        guild_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get the admin/owner team members of a guild
        """
        try:
            # Delegate to the repository
            team_data, total = await self.guild_repository.get_guild_team(guild_id, limit)
            
            # Transform the data to match our response model
            team_members = []
            for member in team_data:
                team_members.append({
                    "discordId": member["discordId"],
                    "discordUsername": member["discordUsername"],
                    "discordUserAvatarURL": member.get("discordUserAvatarURL"),
                    "guildId": member["guildId"],
                    "userType": member["userType"],
                    "joinedAt": member.get("joinedAt")
                })
            
            return {
                "total": total,
                "team": team_members
            }
        except Exception as e:
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving guild team: {str(e)}"
        )

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
        existing_guild = await self.guild_repository.get_by_guild_id(guild_id)
        if not existing_guild:
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
        print("Card image URL:", card_image_url)
        
        # Update guild with new card image URL
        guild_update = GuildUpdate(guildCardImageURL=card_image_url, updatedAt=datetime.now())
        return await self.guild_repository.update(existing_guild.id, guild_update)
    
    async def exchange_guild_points(
        self, 
        guild_id: str, 
        exchange_type: str,
        points_amount: int
    ) -> Dict[str, Any]:
        """
        Exchange points between reserved and vault in a guild
        """
        # Check if guild exists
        guild = await self.guild_repository.get_by_id(guild_id)
        if not guild:
            try:
                # Try with Discord ID if MongoDB ID lookup fails
                guild = await self.guild_repository.get_by_guild_id(guild_id)
                guild_id = str(guild.id)  # Use MongoDB ID for updates
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Guild with ID {guild_id} not found"
                )
        
        # Get current values for response
        current_reserve = guild.analytics.reservedPoints
        current_vault = guild.analytics.vault
        
        # Check if enough points are available for the exchange
        if exchange_type == "reserve_to_vault":
            if current_reserve < points_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient reserve points. Available: {current_reserve}, Requested: {points_amount}"
                )
            new_reserve = current_reserve - points_amount
            new_vault = current_vault + points_amount
        else:  # vault_to_reserve
            if current_vault < points_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient vault points. Available: {current_vault}, Requested: {points_amount}"
                )
            new_reserve = current_reserve + points_amount
            new_vault = current_vault - points_amount
        
        # Update analytics with new values
        analytics_update = {
            "reservedPoints": new_reserve,
            "vault": new_vault
        }
        
        # Update guild
        updated_guild = await self.guild_repository.update_analytics_fields(guild_id, analytics_update)
        
        if not updated_guild:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update guild points"
            )
        
        exchange_direction = "reserve to vault" if exchange_type == "reserve_to_vault" else "vault to reserve"
        
        return {
            "success": True,
            "previous_reserve_points": current_reserve,
            "new_reserve_points": updated_guild.analytics.reservedPoints,
            "previous_vault_points": current_vault,
            "new_vault_points": updated_guild.analytics.vault,
            "message": f"Successfully exchanged {points_amount} points from {exchange_direction}"
        }