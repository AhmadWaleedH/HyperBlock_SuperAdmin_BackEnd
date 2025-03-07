from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models.auction import (
    AuctionModel, AuctionCreate, AuctionUpdate, AuctionFilter, 
    AuctionListResponse, PlaceBidModel, AuctionAnalytics
)
from ...models.user import PaginationParams
from ...services.auction_service import AuctionService
from ...db.repositories.auctions import AuctionRepository
from ...db.database import get_database
from ..dependencies import get_current_admin

router = APIRouter()

async def get_auction_service(database = Depends(get_database)) -> AuctionService:
    auction_repository = AuctionRepository(database)
    return AuctionService(auction_repository)

@router.post("/", response_model=AuctionModel, status_code=status.HTTP_201_CREATED)
async def create_auction(
    auction_data: AuctionCreate,
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Create a new auction
    """
    return await auction_service.create_auction(auction_data)

@router.get("/{auction_id}", response_model=AuctionModel)
async def get_auction(
    auction_id: str = Path(..., title="The ID of the auction to get"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Get an auction by ID
    """
    return await auction_service.get_auction(auction_id)

@router.get("/guild/{guild_id}", response_model=AuctionListResponse)
async def get_auctions_by_guild(
    guild_id: str = Path(..., title="The Guild ID to get auctions for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Get auctions by Guild ID
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await auction_service.get_auctions_by_guild(guild_id, pagination)

@router.patch("/{auction_id}", response_model=AuctionModel)
async def update_auction(
    auction_data: AuctionUpdate,
    auction_id: str = Path(..., title="The ID of the auction to update"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Update an auction
    """
    return await auction_service.update_auction(auction_id, auction_data)

@router.delete("/{auction_id}")
async def delete_auction(
    auction_id: str = Path(..., title="The ID of the auction to delete"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Delete an auction
    """
    return await auction_service.delete_auction(auction_id)

@router.post("/{auction_id}/bid", response_model=AuctionModel)
async def place_bid(
    bid_data: PlaceBidModel,
    auction_id: str = Path(..., title="The ID of the auction to bid on"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Place a bid on an auction
    """
    return await auction_service.place_bid(auction_id, bid_data)

@router.post("/{auction_id}/end", response_model=AuctionModel)
async def end_auction(
    auction_id: str = Path(..., title="The ID of the auction to end"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    End an auction and determine the winner
    """
    return await auction_service.end_auction(auction_id)

@router.post("/{auction_id}/cancel", response_model=AuctionModel)
async def cancel_auction(
    auction_id: str = Path(..., title="The ID of the auction to cancel"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Cancel an auction
    """
    return await auction_service.cancel_auction(auction_id)

@router.get("/", response_model=AuctionListResponse)
async def list_auctions(
    guildId: Optional[str] = Query(None, description="Filter by Guild ID"),
    status: Optional[str] = Query(None, description="Filter by auction status"),
    chain: Optional[str] = Query(None, description="Filter by blockchain chain"),
    has_bids: Optional[bool] = Query(None, description="Filter auctions with bids"),
    min_bid: Optional[float] = Query(None, description="Minimum current bid"),
    max_bid: Optional[float] = Query(None, description="Maximum current bid"),
    bidder_id: Optional[str] = Query(None, description="Filter by bidder ID"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    List auctions with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = AuctionFilter(
        guildId=guildId,
        status=status,
        chain=chain,
        has_bids=has_bids,
        min_bid=min_bid,
        max_bid=max_bid,
        bidder_id=bidder_id,
        created_after=created_after,
        created_before=created_before
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await auction_service.get_auctions(filter_params, pagination)

@router.get("/search/", response_model=AuctionListResponse)
async def search_auctions(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Search auctions by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await auction_service.search_auctions(query, pagination)

@router.get("/analytics/summary", response_model=AuctionAnalytics)
async def get_auction_analytics(
    auction_service: AuctionService = Depends(get_auction_service)
):
    """
    Get analytics summary for all auctions
    """
    return await auction_service.get_analytics()