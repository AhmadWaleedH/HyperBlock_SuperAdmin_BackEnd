from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, UploadFile, status
from datetime import datetime

from ..db.repositories.users import UserRepository
from ..models.user import UserModel, UserCreate, UserUpdate, UserFilter, UserListResponse, PaginationParams

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

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