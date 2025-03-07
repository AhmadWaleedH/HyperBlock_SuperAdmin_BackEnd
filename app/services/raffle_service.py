from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.raffles import RaffleRepository
from ..models.raffle import (
    RaffleModel, RaffleCreate, RaffleUpdate, RaffleFilter, 
    RaffleListResponse, AddParticipantModel, DrawWinnersModel, RaffleAnalytics
)
from ..models.user import PaginationParams

class RaffleService:
    def __init__(self, raffle_repository: RaffleRepository):
        self.raffle_repository = raffle_repository

    async def create_raffle(self, raffle_data: RaffleCreate) -> RaffleModel:
        """
        Create a new raffle
        """
        # Validate number of winners is at least 1
        if raffle_data.numWinners < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of winners must be at least 1"
            )
        
        # Validate entry cost is non-negative
        if raffle_data.entryCost < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry cost cannot be negative"
            )
            
        # Check if entries are limited and validate
        if raffle_data.entriesLimited is not None and raffle_data.entriesLimited <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="If entries are limited, the limit must be positive"
            )
        
        return await self.raffle_repository.create(raffle_data)

    async def get_raffle(self, raffle_id: str) -> RaffleModel:
        """
        Get a raffle by ID
        """
        raffle = await self.raffle_repository.get_by_id(raffle_id)
        if not raffle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raffle with ID {raffle_id} not found"
            )
        return raffle

    async def get_raffles_by_guild(self, guild_id: str, pagination: PaginationParams) -> RaffleListResponse:
        """
        Get raffles by Guild ID
        """
        raffles, total = await self.raffle_repository.get_raffles_by_guild_id(guild_id, pagination)
        return RaffleListResponse(total=total, raffles=raffles)

    async def update_raffle(self, raffle_id: str, raffle_data: RaffleUpdate) -> RaffleModel:
        """
        Update a raffle
        """
        # Check if raffle exists
        existing_raffle = await self.raffle_repository.get_by_id(raffle_id)
        if not existing_raffle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raffle with ID {raffle_id} not found"
            )
        
        # Validation for numberOfWinners and entryCost if provided
        if raffle_data.numWinners is not None and raffle_data.numWinners < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of winners must be at least 1"
            )
            
        if raffle_data.entryCost is not None and raffle_data.entryCost < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry cost cannot be negative"
            )
            
        if raffle_data.entriesLimited is not None and raffle_data.entriesLimited <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="If entries are limited, the limit must be positive"
            )
        
        # Check if raffle is expired and we're trying to make it active
        if existing_raffle.isExpired and raffle_data.isExpired is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reactivate an expired raffle"
            )
        
        # Perform update
        updated_raffle = await self.raffle_repository.update(raffle_id, raffle_data)
        return updated_raffle

    async def delete_raffle(self, raffle_id: str) -> Dict[str, Any]:
        """
        Delete a raffle
        """
        # Check if raffle exists
        existing_raffle = await self.raffle_repository.get_by_id(raffle_id)
        if not existing_raffle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raffle with ID {raffle_id} not found"
            )
        
        # Perform deletion
        success = await self.raffle_repository.delete(raffle_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete raffle"
            )
        
        return {"message": f"Raffle with ID {raffle_id} deleted successfully"}

    async def add_participant(self, raffle_id: str, participant_data: AddParticipantModel) -> RaffleModel:
        """
        Add a participant to a raffle
        """
        # Check if raffle exists
        existing_raffle = await self.raffle_repository.get_by_id(raffle_id)
        if not existing_raffle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raffle with ID {raffle_id} not found"
            )
        
        # Check if raffle is expired
        if existing_raffle.isExpired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join an expired raffle"
            )
        
        # Check if entries are limited
        if existing_raffle.entriesLimited is not None and existing_raffle.totalParticipants >= existing_raffle.entriesLimited:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Raffle has reached its maximum number of participants"
            )
        
        # Add the participant
        updated_raffle = await self.raffle_repository.add_participant(raffle_id, participant_data)
        if not updated_raffle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add participant to raffle"
            )
        
        return updated_raffle

    async def draw_winners(self, raffle_id: str, draw_data: DrawWinnersModel) -> RaffleModel:
        """
        Draw winners for a raffle
        """
        # Check if raffle exists
        existing_raffle = await self.raffle_repository.get_by_id(raffle_id)
        if not existing_raffle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raffle with ID {raffle_id} not found"
            )
        
        # Check if there are participants
        if existing_raffle.totalParticipants == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot draw winners for a raffle with no participants"
            )
        
        # Check if all winners have already been drawn
        if len(existing_raffle.winners) >= existing_raffle.numWinners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All winners have already been drawn for this raffle"
            )
        
        # Draw winners
        updated_raffle = await self.raffle_repository.draw_winners(raffle_id, draw_data)
        if not updated_raffle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to draw winners for raffle"
            )
        
        return updated_raffle

    async def expire_raffle(self, raffle_id: str) -> RaffleModel:
        """
        Mark a raffle as expired
        """
        # Check if raffle exists
        existing_raffle = await self.raffle_repository.get_by_id(raffle_id)
        if not existing_raffle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raffle with ID {raffle_id} not found"
            )
        
        # Check if raffle is already expired
        if existing_raffle.isExpired:
            return existing_raffle
        
        # Mark as expired
        updated_raffle = await self.raffle_repository.expire_raffle(raffle_id)
        if not updated_raffle:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to expire raffle"
            )
        
        return updated_raffle

    async def get_raffles(
        self, 
        filter_params: RaffleFilter,
        pagination: PaginationParams
    ) -> RaffleListResponse:
        """
        Get raffles with filters and pagination
        """
        raffles, total = await self.raffle_repository.get_all_with_filters(filter_params, pagination)
        return RaffleListResponse(total=total, raffles=raffles)

    async def search_raffles(
        self, 
        query: str,
        pagination: PaginationParams
    ) -> RaffleListResponse:
        """
        Search raffles by a query string
        """
        raffles, total = await self.raffle_repository.search(query, pagination)
        return RaffleListResponse(total=total, raffles=raffles)
    
    async def get_analytics(self) -> RaffleAnalytics:
        """
        Get raffle analytics
        """
        return await self.raffle_repository.get_raffle_analytics()