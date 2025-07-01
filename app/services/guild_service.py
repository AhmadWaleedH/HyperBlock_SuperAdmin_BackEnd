from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, UploadFile, status
from datetime import datetime

from app.services.s3_service import S3Service

from ..db.repositories.guilds import GuildRepository
from ..models.guild import CardConfig, CardConfigResponse, CardUploadResponse, GuildModel, GuildCreate, GuildUpdate, GuildFilter, GuildListResponse
from ..models.user import PaginationParams, UserModel

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
    
    async def upload_card_component(self, guild_id: str, file: UploadFile, component_type: str, current_user: UserModel) -> GuildModel:
        """Upload a card component for a guild"""
        
        # Verify permissions
        await self._verify_guild_permissions(guild_id, current_user)
        
        # Get existing guild
        existing_guild = await self.guild_repository.get_by_id(guild_id)
        if not existing_guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Upload file to S3
        s3_service = S3Service()
        
        # Delete old file if exists
        old_url = None
        if component_type == "background":
            old_url = existing_guild.cardConfig.cardImageBackground
        elif component_type == "community_icon":
            old_url = existing_guild.cardConfig.communityIcon
        elif component_type == "hb_icon":
            old_url = existing_guild.cardConfig.hbIcon
        
        if old_url:
            await s3_service.delete_file(old_url)
        
        # Upload new file
        new_url = await s3_service.upload_file(file, folder=f"guild-cards/{guild_id}/{component_type}")
        
        # Update card config
        card_config = existing_guild.cardConfig.dict()
        if component_type == "background":
            card_config["cardImageBackground"] = new_url
        elif component_type == "community_icon":
            card_config["communityIcon"] = new_url
        elif component_type == "hb_icon":
            card_config["hbIcon"] = new_url
        
        # Update guild
        guild_update = GuildUpdate(cardConfig=CardConfig(**card_config), updatedAt=datetime.now())
        await self.guild_repository.update(existing_guild.id, guild_update)
        
        # Return success response instead of guild object
        component_names = {
            "background": "Background Image",
            "community_icon": "Community Icon", 
            "hb_icon": "HB Icon"
        }
        
        return CardUploadResponse(
            success=True,
            message=f"{component_names[component_type]} uploaded successfully",
            component=component_type,
            imageUrl=new_url
        )

    async def update_card_token_name(self, guild_id: str, token_name: str, current_user: UserModel) -> GuildModel:
        """Update token name for a guild"""
        
        # Verify permissions
        await self._verify_guild_permissions(guild_id, current_user)
        
        # Get existing guild
        existing_guild = await self.guild_repository.get_by_id(guild_id)
        
        # Update card config
        card_config = existing_guild.cardConfig.dict()
        card_config["tokenName"] = token_name or ""
        
        # Update guild
        guild_update = GuildUpdate(cardConfig=CardConfig(**card_config), updatedAt=datetime.now())
        await self.guild_repository.update(existing_guild.id, guild_update)

    async def get_card_config(self, guild_id: str) -> CardConfigResponse:
        """Get card configuration for a guild"""
        
        existing_guild = await self.guild_repository.get_by_id(guild_id)
        if not existing_guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        return CardConfigResponse(**existing_guild.cardConfig.dict())

    # Helper methods
    async def _verify_guild_permissions(self, guild_id: str, current_user: UserModel):
        """Verify user has permissions to modify guild"""
        guild = await self.guild_repository.get_by_id(guild_id)
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        is_guild_owner = guild.ownerId == current_user.id
        is_guild_admin = any(
            membership.guildId == guild.guildId and membership.userType in ["admin", "owner"]
            for membership in current_user.serverMemberships
        )
        is_system_admin = current_user.userGlobalStatus == "admin"
        
        if not (is_guild_owner or is_guild_admin or is_system_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this guild"
            )

    async def _get_guild_by_id_or_discord_id(self, guild_id: str) -> GuildModel:
        """Get guild by ID or Discord ID"""
        try:
            guild = await self.guild_repository.get_by_id(guild_id)
        except Exception:
            guild = await self.guild_repository.get_by_guild_id(guild_id)
        
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        return guild