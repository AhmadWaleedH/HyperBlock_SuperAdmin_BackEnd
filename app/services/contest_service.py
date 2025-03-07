from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.contests import ContestRepository
from ..models.contest import (
    ContestModel, ContestCreate, ContestUpdate, ContestFilter, 
    ContestListResponse, MessageVoteUpdate, ContestAnalytics
)
from ..models.user import PaginationParams

class ContestService:
    def __init__(self, contest_repository: ContestRepository):
        self.contest_repository = contest_repository

    async def create_contest(self, contest_data: ContestCreate) -> ContestModel:
        """
        Create a new contest
        """
        # Validate number of winners is at least 1
        if contest_data.numberOfWinners < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of winners must be at least 1"
            )
        
        # If pointsForWinners is provided, validate its length matches numberOfWinners
        if contest_data.pointsForWinners and len(contest_data.pointsForWinners) != contest_data.numberOfWinners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Length of pointsForWinners must match numberOfWinners"
            )
        
        return await self.contest_repository.create(contest_data)

    async def get_contest(self, contest_id: str) -> ContestModel:
        """
        Get a contest by ID
        """
        contest = await self.contest_repository.get_by_id(contest_id)
        if not contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contest with ID {contest_id} not found"
            )
        return contest

    async def get_contests_by_guild(self, guild_id: str, pagination: PaginationParams) -> ContestListResponse:
        """
        Get contests by Guild ID
        """
        contests, total = await self.contest_repository.get_contests_by_guild_id(guild_id, pagination)
        return ContestListResponse(total=total, contests=contests)

    async def update_contest(self, contest_id: str, contest_data: ContestUpdate) -> ContestModel:
        """
        Update a contest
        """
        # Check if contest exists
        existing_contest = await self.contest_repository.get_by_id(contest_id)
        if not existing_contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contest with ID {contest_id} not found"
            )
        
        # Validation for numberOfWinners and pointsForWinners
        number_of_winners = contest_data.numberOfWinners or existing_contest.numberOfWinners
        points_for_winners = contest_data.pointsForWinners or existing_contest.pointsForWinners
        
        if number_of_winners < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of winners must be at least 1"
            )
        
        if points_for_winners and len(points_for_winners) != number_of_winners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Length of pointsForWinners must match numberOfWinners"
            )
        
        # Perform update
        updated_contest = await self.contest_repository.update(contest_id, contest_data)
        return updated_contest

    async def delete_contest(self, contest_id: str) -> Dict[str, Any]:
        """
        Delete a contest
        """
        # Check if contest exists
        existing_contest = await self.contest_repository.get_by_id(contest_id)
        if not existing_contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contest with ID {contest_id} not found"
            )
        
        # Perform deletion
        success = await self.contest_repository.delete(contest_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete contest"
            )
        
        return {"message": f"Contest with ID {contest_id} deleted successfully"}

    async def add_vote(self, contest_id: str, vote_data: MessageVoteUpdate) -> ContestModel:
        """
        Add a vote to a contest
        """
        # Check if contest exists
        existing_contest = await self.contest_repository.get_by_id(contest_id)
        if not existing_contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contest with ID {contest_id} not found"
            )
        
        # Check if contest is active
        if existing_contest.isActive is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot vote on an inactive contest"
            )
        
        # Add the vote
        updated_contest = await self.contest_repository.add_vote(contest_id, vote_data)
        if not updated_contest:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add vote to contest"
            )
        
        return updated_contest

    async def get_contests(
        self, 
        filter_params: ContestFilter,
        pagination: PaginationParams
    ) -> ContestListResponse:
        """
        Get contests with filters and pagination
        """
        contests, total = await self.contest_repository.get_all_with_filters(filter_params, pagination)
        return ContestListResponse(total=total, contests=contests)

    async def search_contests(
        self, 
        query: str,
        pagination: PaginationParams
    ) -> ContestListResponse:
        """
        Search contests by a query string
        """
        contests, total = await self.contest_repository.search(query, pagination)
        return ContestListResponse(total=total, contests=contests)
    
    async def get_analytics(self) -> ContestAnalytics:
        """
        Get contest analytics
        """
        return await self.contest_repository.get_contest_analytics()