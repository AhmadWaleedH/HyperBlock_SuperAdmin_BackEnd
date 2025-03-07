from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.auctions import AuctionRepository
from ..models.auction import (
    AuctionModel, AuctionCreate, AuctionUpdate, AuctionFilter, 
    AuctionListResponse, PlaceBidModel, AuctionAnalytics
)
from ..models.user import PaginationParams

class AuctionService:
    def __init__(self, auction_repository: AuctionRepository):
        self.auction_repository = auction_repository

    async def create_auction(self, auction_data: AuctionCreate) -> AuctionModel:
        """
        Create a new auction
        """
        # Validate quantity is non-negative
        if auction_data.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be non-negative"
            )
        
        # Validate minimum bid is non-negative
        if auction_data.minimumBid < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum bid cannot be negative"
            )
        
        # Validate duration is in the future
        if auction_data.duration < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction duration must be in the future"
            )
        
        return await self.auction_repository.create(auction_data)

    async def get_auction(self, auction_id: str) -> AuctionModel:
        """
        Get an auction by ID
        """
        auction = await self.auction_repository.get_by_id(auction_id)
        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auction with ID {auction_id} not found"
            )
        return auction

    async def get_auctions_by_guild(self, guild_id: str, pagination: PaginationParams) -> AuctionListResponse:
        """
        Get auctions by Guild ID
        """
        auctions, total = await self.auction_repository.get_auctions_by_guild_id(guild_id, pagination)
        return AuctionListResponse(total=total, auctions=auctions)

    async def update_auction(self, auction_id: str, auction_data: AuctionUpdate) -> AuctionModel:
        """
        Update an auction
        """
        # Check if auction exists
        existing_auction = await self.auction_repository.get_by_id(auction_id)
        if not existing_auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auction with ID {auction_id} not found"
            )
        
        # Validation for quantity if provided
        if auction_data.quantity is not None and auction_data.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be non-negative"
            )
            
        # Validation for minimumBid if provided
        if auction_data.minimumBid is not None and auction_data.minimumBid < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum bid cannot be negative"
            )
            
        # Validation for duration if provided
        if auction_data.duration is not None and auction_data.duration < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction duration must be in the future"
            )
        
        # Prevent updating an ended or cancelled auction
        if existing_auction.status != "active" and auction_data.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update an auction with status '{existing_auction.status}'"
            )
        
        # Perform update
        updated_auction = await self.auction_repository.update(auction_id, auction_data)
        return updated_auction

    async def delete_auction(self, auction_id: str) -> Dict[str, Any]:
        """
        Delete an auction
        """
        # Check if auction exists
        existing_auction = await self.auction_repository.get_by_id(auction_id)
        if not existing_auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auction with ID {auction_id} not found"
            )
        
        # Prevent deleting an auction with bids
        if existing_auction.bidders and len(existing_auction.bidders) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete an auction that has bids"
            )
        
        # Perform deletion
        success = await self.auction_repository.delete(auction_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete auction"
            )
        
        return {"message": f"Auction with ID {auction_id} deleted successfully"}

    async def place_bid(self, auction_id: str, bid_data: PlaceBidModel) -> AuctionModel:
        """
        Place a bid on an auction
        """
        # Check if auction exists
        existing_auction = await self.auction_repository.get_by_id(auction_id)
        if not existing_auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auction with ID {auction_id} not found"
            )
        
        # Check if auction is active
        if existing_auction.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot bid on an auction with status '{existing_auction.status}'"
            )
        
        # Check if auction has expired by duration
        if existing_auction.duration < datetime.now():
            # Auto-end the auction if it has expired
            await self.auction_repository.update(
                auction_id, 
                AuctionUpdate(status="ended")
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot bid on an expired auction"
            )
        
        # Check if bid amount is high enough
        if bid_data.bidAmount <= existing_auction.currentBid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid amount must be higher than current bid of {existing_auction.currentBid}"
            )
        
        # Place the bid
        updated_auction = await self.auction_repository.place_bid(auction_id, bid_data)
        if not updated_auction:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to place bid on auction"
            )
        
        return updated_auction

    async def end_auction(self, auction_id: str) -> AuctionModel:
        """
        End an auction and determine the winner
        """
        # Check if auction exists
        existing_auction = await self.auction_repository.get_by_id(auction_id)
        if not existing_auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auction with ID {auction_id} not found"
            )
        
        # Check if auction is already ended or cancelled
        if existing_auction.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot end an auction with status '{existing_auction.status}'"
            )
        
        # End the auction
        updated_auction = await self.auction_repository.end_auction(auction_id)
        if not updated_auction:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to end auction"
            )
        
        return updated_auction

    async def cancel_auction(self, auction_id: str) -> AuctionModel:
        """
        Cancel an auction
        """
        # Check if auction exists
        existing_auction = await self.auction_repository.get_by_id(auction_id)
        if not existing_auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auction with ID {auction_id} not found"
            )
        
        # Check if auction is already ended or cancelled
        if existing_auction.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel an auction with status '{existing_auction.status}'"
            )
        
        # Cancel the auction
        updated_auction = await self.auction_repository.cancel_auction(auction_id)
        if not updated_auction:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel auction"
            )
        
        return updated_auction

    async def get_auctions(
        self, 
        filter_params: AuctionFilter,
        pagination: PaginationParams
    ) -> AuctionListResponse:
        """
        Get auctions with filters and pagination
        """
        auctions, total = await self.auction_repository.get_all_with_filters(filter_params, pagination)
        return AuctionListResponse(total=total, auctions=auctions)

    async def search_auctions(
        self, 
        query: str,
        pagination: PaginationParams
    ) -> AuctionListResponse:
        """
        Search auctions by a query string
        """
        auctions, total = await self.auction_repository.search(query, pagination)
        return AuctionListResponse(total=total, auctions=auctions)
    
    async def get_analytics(self) -> AuctionAnalytics:
        """
        Get auction analytics
        """
        return await self.auction_repository.get_auction_analytics()