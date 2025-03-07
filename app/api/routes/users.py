from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List
from datetime import datetime

from app.api.dependencies import get_current_admin

from ...models.user import (
    UserModel, UserCreate, UserUpdate, UserFilter, 
    UserListResponse, PaginationParams
)
from ...services.user_service import UserService
from ...db.repositories.users import UserRepository
from ...db.database import get_database

router = APIRouter()

async def get_user_service(database = Depends(get_database)) -> UserService:
    user_repository = UserRepository(database)
    return UserService(user_repository)

@router.post("/", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user
    """
    return await user_service.create_user(user_data)

@router.get("/{user_id}", response_model=UserModel)
async def get_user(
    user_id: str = Path(..., title="The ID of the user to get"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by ID
    """
    return await user_service.get_user(user_id)

@router.get("/discord/{discord_id}", response_model=UserModel)
async def get_user_by_discord_id(
    discord_id: str = Path(..., title="The Discord ID of the user to get"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by Discord ID
    """
    return await user_service.get_user_by_discord_id(discord_id)

@router.patch("/{user_id}", response_model=UserModel)
async def update_user(
    user_data: UserUpdate,
    user_id: str = Path(..., title="The ID of the user to update"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update a user
    """
    return await user_service.update_user(user_id, user_data)

@router.delete("/{user_id}", dependencies=[Depends(get_current_admin)])
async def delete_user(
    user_id: str = Path(..., title="The ID of the user to delete"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete a user
    """
    return await user_service.delete_user(user_id)

@router.get("/", response_model=UserListResponse)
async def list_users(
    subscription_tier: Optional[str] = Query(None, description="Filter by subscription tier"),
    status: Optional[str] = Query(None, description="Filter by user status"),
    wallet_type: Optional[str] = Query(None, description="Filter by wallet type"),
    min_points: Optional[int] = Query(None, description="Minimum hyperblock points"),
    max_points: Optional[int] = Query(None, description="Maximum hyperblock points"),
    discord_username: Optional[str] = Query(None, description="Filter by Discord username"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    user_service: UserService = Depends(get_user_service)
):
    """
    List users with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = UserFilter(
        subscription_tier=subscription_tier,
        status=status,
        wallet_type=wallet_type,
        min_points=min_points,
        max_points=max_points,
        discord_username=discord_username,
        created_after=created_after,
        created_before=created_before
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await user_service.get_users(filter_params, pagination)

@router.get("/search/", response_model=UserListResponse)
async def search_users(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search users by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await user_service.search_users(query, pagination)