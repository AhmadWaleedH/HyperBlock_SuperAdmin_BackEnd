from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, UploadFile, status
from datetime import datetime

from app.db.repositories.guilds import GuildRepository

from ..db.repositories.users import UserRepository
from ..models.user import UserModel, UserCreate, UserUpdate, UserFilter, UserListResponse, PaginationParams

class UserService:
    def __init__(self, user_repository: UserRepository, guild_repository: GuildRepository):
        self.user_repository = user_repository
        self.guild_repository = guild_repository

    async def create_user(self, user_data: UserCreate) -> UserModel:
        """
        Create a new user
        """
        # Check if user with discord_id already exists
        existing_user = await self.user_repository.get_by_discord_id(user_data.discordId)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with Discord ID {user_data.discordId} already exists"
            )
        
        return await self.user_repository.create(user_data)

    async def get_user(self, user_id: str) -> UserModel:
        """
        Get a user by ID
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user

    async def get_user_by_discord_id(self, discord_id: str) -> UserModel:
        """
        Get a user by Discord ID
        """
        user = await self.user_repository.get_by_discord_id(discord_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with Discord ID {discord_id} not found"
            )
        return user

    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserModel:
        """
        Update a user
        """
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Perform update
        updated_user = await self.user_repository.update(user_id, user_data)
        return updated_user

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user
        """
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Perform deletion
        success = await self.user_repository.delete(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        return {"message": f"User with ID {user_id} deleted successfully"}

    async def get_users(
        self, 
        filter_params: UserFilter,
        pagination: PaginationParams
    ) -> UserListResponse:
        """
        Get users with filters and pagination
        """
        users, total = await self.user_repository.get_all_with_filters(filter_params, pagination)
        return UserListResponse(total=total, users=users)

    async def search_users(
        self, 
        query: str,
        pagination: PaginationParams
    ) -> UserListResponse:
        """
        Search users by a query string
        """
        users, total = await self.user_repository.search(query, pagination)
        return UserListResponse(total=total, users=users)
    
    async def upload_card_image(self, user_id: str, file: UploadFile) -> UserModel:
        """
        Upload a card image for a user and update their profile
        """
        # Check if user exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Upload file to S3
        from ..services.s3_service import S3Service
        s3_service = S3Service()
        
        # If user already has a card image, delete it first
        if existing_user.cardImageUrl:
            await s3_service.delete_file(existing_user.cardImageUrl)
        
        # Upload new image
        card_image_url = await s3_service.upload_file(
            file, 
            folder=f"user-cards/{user_id}" # remove /{user_id} to store all user cards in the same folder
        )
        
        # Update user with new card image URL
        user_update = UserUpdate(cardImageUrl=card_image_url, updatedAt=datetime.now())
        return await self.user_repository.update(user_id, user_update)

    
    # Add to services/user_service.py
    async def exchange_guild_points_to_global(
        self, 
        user_id: str, 
        guild_id: str, 
        points_amount: int
    ) -> Dict[str, Any]:
        """
        Exchange guild points to global points
        """
        # Check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if user is a member of the guild
        guild_membership = next((m for m in user.serverMemberships if m.guildId == guild_id), None)
        if not guild_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User is not a member of guild with ID {guild_id}"
            )
        
        # Check if guild exists and get its ERC value
        guild = await self.guild_repository.get_by_guild_id(guild_id)
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Get the ERC value from the guild data
        erc_value = guild.analytics.ERC
        if not erc_value or erc_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ERC value for this guild"
            )
        
        # Check if guild membership is active
        if guild_membership.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guild membership is not active"
            )
        
        # Check if user has enough points in the guild
        if not guild_membership.points or guild_membership.points < points_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient guild points. Available: {guild_membership.points or 0}, Requested: {points_amount}"
            )
        
        # Get current values for response
        previous_guild_points = guild_membership.points
        previous_global_points = user.hyperBlockPoints or 0

        # Calculate global points to add based on ERC value
        global_points_to_add = float(points_amount / erc_value)
        
        # Update guild points
        guild_membership.points -= points_amount
        
        # Update global points
        if user.hyperBlockPoints is None:
            user.hyperBlockPoints = global_points_to_add
        else:
            user.hyperBlockPoints += global_points_to_add
        
        # Update user record
        user.updatedAt = datetime.now()
        updated_user = await self.user_repository.update_full(user)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user points"
            )
        
        # Get the updated membership for response
        updated_membership = next((m for m in updated_user.serverMemberships if m.guildId == guild_id), None)
        
        return {
            "success": True,
            "previous_guild_points": previous_guild_points,
            "new_guild_points": updated_membership.points,
            "previous_global_points": previous_global_points,
            "new_global_points": updated_user.hyperBlockPoints,
            "message": f"Successfully exchanged {points_amount} guild points to global points"
        }