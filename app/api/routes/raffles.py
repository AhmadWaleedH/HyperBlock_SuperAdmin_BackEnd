from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models.raffle import (
    RaffleModel, RaffleCreate, RaffleUpdate, RaffleFilter, 
    RaffleListResponse, AddParticipantModel, DrawWinnersModel, RaffleAnalytics
)
from ...models.user import PaginationParams
from ...services.raffle_service import RaffleService
from ...db.repositories.raffles import RaffleRepository
from ...db.database import get_database
from ..dependencies import get_current_admin

router = APIRouter()

async def get_raffle_service(database = Depends(get_database)) -> RaffleService:
    raffle_repository = RaffleRepository(database)
    return RaffleService(raffle_repository)

@router.post("/", response_model=RaffleModel, status_code=status.HTTP_201_CREATED)
async def create_raffle(
    raffle_data: RaffleCreate,
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Create a new raffle
    """
    return await raffle_service.create_raffle(raffle_data)

@router.get("/{raffle_id}", response_model=RaffleModel)
async def get_raffle(
    raffle_id: str = Path(..., title="The ID of the raffle to get"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Get a raffle by ID
    """
    return await raffle_service.get_raffle(raffle_id)

@router.get("/guild/{guild_id}", response_model=RaffleListResponse)
async def get_raffles_by_guild(
    guild_id: str = Path(..., title="The Guild ID to get raffles for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Get raffles by Guild ID
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await raffle_service.get_raffles_by_guild(guild_id, pagination)

@router.patch("/{raffle_id}", response_model=RaffleModel)
async def update_raffle(
    raffle_data: RaffleUpdate,
    raffle_id: str = Path(..., title="The ID of the raffle to update"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Update a raffle
    """
    return await raffle_service.update_raffle(raffle_id, raffle_data)

@router.delete("/{raffle_id}")
async def delete_raffle(
    raffle_id: str = Path(..., title="The ID of the raffle to delete"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Delete a raffle
    """
    return await raffle_service.delete_raffle(raffle_id)

@router.post("/{raffle_id}/participants", response_model=RaffleModel)
async def add_participant(
    participant_data: AddParticipantModel,
    raffle_id: str = Path(..., title="The ID of the raffle to add participant to"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Add a participant to a raffle
    """
    return await raffle_service.add_participant(raffle_id, participant_data)

@router.post("/{raffle_id}/draw", response_model=RaffleModel)
async def draw_winners(
    draw_data: DrawWinnersModel,
    raffle_id: str = Path(..., title="The ID of the raffle to draw winners for"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Draw winners for a raffle
    """
    return await raffle_service.draw_winners(raffle_id, draw_data)

@router.post("/{raffle_id}/expire", response_model=RaffleModel)
async def expire_raffle(
    raffle_id: str = Path(..., title="The ID of the raffle to expire"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Mark a raffle as expired
    """
    return await raffle_service.expire_raffle(raffle_id)

@router.get("/", response_model=RaffleListResponse)
async def list_raffles(
    guildId: Optional[str] = Query(None, description="Filter by Guild ID"),
    isExpired: Optional[bool] = Query(None, description="Filter by expired status"),
    chain: Optional[str] = Query(None, description="Filter by blockchain chain"),
    has_winners: Optional[bool] = Query(None, description="Filter raffles with winners"),
    entry_cost_min: Optional[int] = Query(None, description="Minimum entry cost"),
    entry_cost_max: Optional[int] = Query(None, description="Maximum entry cost"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    List raffles with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = RaffleFilter(
        guildId=guildId,
        isExpired=isExpired,
        chain=chain,
        has_winners=has_winners,
        entry_cost_min=entry_cost_min,
        entry_cost_max=entry_cost_max,
        created_after=created_after,
        created_before=created_before
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await raffle_service.get_raffles(filter_params, pagination)

@router.get("/search/", response_model=RaffleListResponse)
async def search_raffles(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Search raffles by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await raffle_service.search_raffles(query, pagination)

@router.get("/analytics/summary", response_model=RaffleAnalytics)
async def get_raffle_analytics(
    raffle_service: RaffleService = Depends(get_raffle_service)
):
    """
    Get analytics summary for all raffles
    """
    return await raffle_service.get_analytics()