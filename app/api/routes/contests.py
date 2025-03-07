from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models.contest import (
    ContestModel, ContestCreate, ContestUpdate, ContestFilter, 
    ContestListResponse, MessageVoteUpdate, ContestAnalytics
)
from ...models.user import PaginationParams
from ...services.contest_service import ContestService
from ...db.repositories.contests import ContestRepository
from ...db.database import get_database
from ..dependencies import get_current_admin

router = APIRouter()

async def get_contest_service(database = Depends(get_database)) -> ContestService:
    contest_repository = ContestRepository(database)
    return ContestService(contest_repository)

@router.post("/", response_model=ContestModel, status_code=status.HTTP_201_CREATED)
async def create_contest(
    contest_data: ContestCreate,
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Create a new contest
    """
    return await contest_service.create_contest(contest_data)

@router.get("/{contest_id}", response_model=ContestModel)
async def get_contest(
    contest_id: str = Path(..., title="The ID of the contest to get"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Get a contest by ID
    """
    return await contest_service.get_contest(contest_id)

@router.get("/guild/{guild_id}", response_model=ContestListResponse)
async def get_contests_by_guild(
    guild_id: str = Path(..., title="The Guild ID to get contests for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Get contests by Guild ID
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await contest_service.get_contests_by_guild(guild_id, pagination)

@router.patch("/{contest_id}", response_model=ContestModel)
async def update_contest(
    contest_data: ContestUpdate,
    contest_id: str = Path(..., title="The ID of the contest to update"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Update a contest
    """
    return await contest_service.update_contest(contest_id, contest_data)

@router.delete("/{contest_id}")
async def delete_contest(
    contest_id: str = Path(..., title="The ID of the contest to delete"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Delete a contest
    """
    return await contest_service.delete_contest(contest_id)

@router.post("/{contest_id}/vote", response_model=ContestModel)
async def add_vote(
    vote_data: MessageVoteUpdate,
    contest_id: str = Path(..., title="The ID of the contest to vote on"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Add a vote to a contest
    """
    return await contest_service.add_vote(contest_id, vote_data)

@router.get("/", response_model=ContestListResponse)
async def list_contests(
    guildId: Optional[str] = Query(None, description="Filter by Guild ID"),
    isActive: Optional[bool] = Query(None, description="Filter by active status"),
    has_participants: Optional[bool] = Query(None, description="Filter contests with participants"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    List contests with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = ContestFilter(
        guildId=guildId,
        isActive=isActive,
        has_participants=has_participants,
        created_after=created_after,
        created_before=created_before
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await contest_service.get_contests(filter_params, pagination)

@router.get("/search/", response_model=ContestListResponse)
async def search_contests(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Search contests by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await contest_service.search_contests(query, pagination)

@router.get("/analytics/summary", response_model=ContestAnalytics)
async def get_contest_analytics(
    contest_service: ContestService = Depends(get_contest_service)
):
    """
    Get analytics summary for all contests
    """
    return await contest_service.get_analytics()