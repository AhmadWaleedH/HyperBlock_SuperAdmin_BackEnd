from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
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