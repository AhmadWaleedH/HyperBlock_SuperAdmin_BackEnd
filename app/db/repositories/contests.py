from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorCursor
from datetime import datetime
from bson import ObjectId

from ...models.contest import (
    ContestModel, ContestCreate, ContestUpdate, ContestFilter, 
    MessageVoteUpdate, ContestAnalytics, ContestStatistics
)
from ...models.user import PaginationParams

class ContestRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.contests

    async def create(self, contest: ContestCreate) -> ContestModel:
        """
        Create a new contest in the database
        """
        contest_data = contest.dict()
        contest_data["createdAt"] = datetime.now()
        contest_data["updatedAt"] = datetime.now()
        
        # Initialize votes as empty list
        contest_data["votes"] = []
        
        result = await self.collection.insert_one(contest_data)
        contest_data["_id"] = result.inserted_id
        
        return ContestModel(**contest_data)

    async def get_by_id(self, contest_id: str) -> Optional[ContestModel]:
        """
        Get a contest by MongoDB ID
        """
        if not ObjectId.is_valid(contest_id):
            return None
            
        contest = await self.collection.find_one({"_id": ObjectId(contest_id)})
        if contest:
            return ContestModel(**contest)
        return None

    async def get_contests_by_guild_id(self, guild_id: str, pagination: PaginationParams) -> Tuple[List[ContestModel], int]:
        """
        Get contests by Guild ID
        """
        query = {"guildId": guild_id}
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        contests = []
        async for contest_doc in cursor:
            contests.append(ContestModel(**contest_doc))
        
        return contests, total

    async def update(self, contest_id: str, contest_update: ContestUpdate) -> Optional[ContestModel]:
        """
        Update a contest
        """
        if not ObjectId.is_valid(contest_id):
            return None
            
        update_data = contest_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(contest_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(contest_id)

    async def delete(self, contest_id: str) -> bool:
        """
        Delete a contest
        """
        if not ObjectId.is_valid(contest_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(contest_id)})
        return result.deleted_count > 0

    async def add_vote(self, contest_id: str, vote_data: MessageVoteUpdate) -> Optional[ContestModel]:
        """
        Add a vote to a contest message
        """
        if not ObjectId.is_valid(contest_id):
            return None
        
        contest = await self.get_by_id(contest_id)
        if not contest:
            return None
        
        # Check if message already exists in votes
        message_exists = False
        
        for vote in contest.votes:
            if vote.messageId == vote_data.messageId:
                message_exists = True
                # Check if user already voted
                user_exists = False
                for user_vote in vote.userVotes:
                    if user_vote.userId == vote_data.userVote.userId:
                        # Update user's vote
                        await self.collection.update_one(
                            {
                                "_id": ObjectId(contest_id), 
                                "votes.messageId": vote_data.messageId,
                                "votes.userVotes.userId": vote_data.userVote.userId
                            },
                            {"$set": {"votes.$.userVotes.$[user].voteCount": vote_data.userVote.voteCount}},
                            array_filters=[{"user.userId": vote_data.userVote.userId}]
                        )
                        user_exists = True
                        break
                
                if not user_exists:
                    # Add new user vote
                    await self.collection.update_one(
                        {"_id": ObjectId(contest_id), "votes.messageId": vote_data.messageId},
                        {"$push": {"votes.$.userVotes": vote_data.userVote.dict()}}
                    )
                break
        
        if not message_exists:
            # Add new message vote
            await self.collection.update_one(
                {"_id": ObjectId(contest_id)},
                {"$push": {"votes": {
                    "messageId": vote_data.messageId,
                    "userVotes": [vote_data.userVote.dict()]
                }}}
            )
        
        # Update the "updatedAt" field
        await self.collection.update_one(
            {"_id": ObjectId(contest_id)},
            {"$set": {"updatedAt": datetime.now()}}
        )
        
        return await self.get_by_id(contest_id)

    async def get_all_with_filters(
        self, 
        filter_params: ContestFilter,
        pagination: PaginationParams
    ) -> Tuple[List[ContestModel], int]:
        """
        Get all contests with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.guildId:
            query["guildId"] = filter_params.guildId
            
        if filter_params.isActive is not None:
            query["isActive"] = filter_params.isActive
            
        if filter_params.created_after:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$gte"] = filter_params.created_after
            
        if filter_params.created_before:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$lte"] = filter_params.created_before
            
        if filter_params.has_participants is not None and filter_params.has_participants:
            query["votes"] = {"$exists": True, "$not": {"$size": 0}}
        
        # Count total documents matching the query
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        contests = []
        async for contest_doc in cursor:
            contests.append(ContestModel(**contest_doc))
        
        return contests, total

    async def search(self, query_string: str, pagination: PaginationParams) -> Tuple[List[ContestModel], int]:
        """
        Search contests by a general query string
        """
        # Building a search query across multiple fields
        query = {
            "$or": [
                {"title": {"$regex": query_string, "$options": "i"}},
                {"description": {"$regex": query_string, "$options": "i"}},
                {"guildId": {"$regex": query_string, "$options": "i"}},
                {"channelId": {"$regex": query_string, "$options": "i"}},
            ]
        }
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        contests = []
        async for contest_doc in cursor:
            contests.append(ContestModel(**contest_doc))
        
        return contests, total
    
    async def get_contest_analytics(self) -> ContestAnalytics:
        """
        Get analytics for all contests
        """
        # Count total contests
        total_contests = await self.collection.count_documents({})
        
        # Count active contests
        active_contests = await self.collection.count_documents({"isActive": True})
        
        # Aggregate contests by guild
        guild_pipeline = [
            {"$group": {"_id": "$guildId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        guild_results = await self.collection.aggregate(guild_pipeline).to_list(length=None)
        contests_by_guild = {item["_id"]: item["count"] for item in guild_results}
        
        # Calculate total votes cast across all contests
        total_votes_pipeline = [
            {"$unwind": {"path": "$votes", "preserveNullAndEmptyArrays": False}},
            {"$unwind": {"path": "$votes.userVotes", "preserveNullAndEmptyArrays": False}},
            {"$group": {"_id": None, "totalVotes": {"$sum": "$votes.userVotes.voteCount"}}}
        ]
        votes_result = await self.collection.aggregate(total_votes_pipeline).to_list(length=None)
        total_votes_cast = votes_result[0]["totalVotes"] if votes_result else 0
        
        # Get top contests by participation
        top_contests_pipeline = [
            {"$unwind": {"path": "$votes", "preserveNullAndEmptyArrays": False}},
            {"$unwind": {"path": "$votes.userVotes", "preserveNullAndEmptyArrays": False}},
            {"$group": {
                "_id": "$_id", 
                "title": {"$first": "$title"},
                "totalVotes": {"$sum": "$votes.userVotes.voteCount"},
                "participants": {"$addToSet": "$votes.userVotes.userId"}
            }},
            {"$addFields": {"participantsCount": {"$size": "$participants"}}},
            {"$sort": {"totalVotes": -1}},
            {"$limit": 5}
        ]
        top_contests_result = await self.collection.aggregate(top_contests_pipeline).to_list(length=None)
        
        top_contests = []
        for contest in top_contests_result:
            top_contests.append(ContestStatistics(
                contest_id=str(contest["_id"]),
                title=contest["title"],
                total_votes=contest["totalVotes"],
                total_participants=contest["participantsCount"]
            ))
        
        return ContestAnalytics(
            total_contests=total_contests,
            active_contests=active_contests,
            total_votes_cast=total_votes_cast,
            contests_by_guild=contests_by_guild,
            top_contests=top_contests
        )