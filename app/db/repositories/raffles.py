from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorCursor
from datetime import datetime
from bson import ObjectId
import random

from ...models.raffle import (
    RaffleModel, RaffleCreate, RaffleUpdate, RaffleFilter, 
    AddParticipantModel, DrawWinnersModel, RaffleAnalytics, RaffleStatistics
)
from ...models.user import PaginationParams

class RaffleRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.giveaways

    async def create(self, raffle: RaffleCreate) -> RaffleModel:
        """
        Create a new raffle in the database
        """
        raffle_data = raffle.dict()
        raffle_data["createdAt"] = datetime.now()
        raffle_data["updatedAt"] = datetime.now()
        raffle_data["totalParticipants"] = 0
        raffle_data["participants"] = []
        raffle_data["winners"] = []
        raffle_data["isExpired"] = False
        
        result = await self.collection.insert_one(raffle_data)
        raffle_data["_id"] = result.inserted_id
        
        return RaffleModel(**raffle_data)

    async def get_by_id(self, raffle_id: str) -> Optional[RaffleModel]:
        """
        Get a raffle by MongoDB ID
        """
        if not ObjectId.is_valid(raffle_id):
            return None
            
        raffle = await self.collection.find_one({"_id": ObjectId(raffle_id)})
        if raffle:
            return RaffleModel(**raffle)
        return None

    async def get_raffles_by_guild_id(self, guild_id: str, pagination: PaginationParams) -> Tuple[List[RaffleModel], int]:
        """
        Get raffles by Guild ID
        """
        query = {"guildId": guild_id}
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        raffles = []
        async for raffle_doc in cursor:
            raffles.append(RaffleModel(**raffle_doc))
        
        return raffles, total

    async def update(self, raffle_id: str, raffle_update: RaffleUpdate) -> Optional[RaffleModel]:
        """
        Update a raffle
        """
        if not ObjectId.is_valid(raffle_id):
            return None
            
        update_data = raffle_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(raffle_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(raffle_id)

    async def delete(self, raffle_id: str) -> bool:
        """
        Delete a raffle
        """
        if not ObjectId.is_valid(raffle_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(raffle_id)})
        return result.deleted_count > 0

    async def add_participant(self, raffle_id: str, participant: AddParticipantModel) -> Optional[RaffleModel]:
        """
        Add a participant to a raffle
        """
        if not ObjectId.is_valid(raffle_id):
            return None
        
        # Check if user is already a participant
        raffle = await self.get_by_id(raffle_id)
        if not raffle:
            return None
        
        # Check if user is already a participant
        participant_exists = False
        for existing_participant in raffle.participants:
            if existing_participant.userId == participant.userId:
                participant_exists = True
                break
        
        if participant_exists:
            # User is already a participant, just return the raffle
            return raffle
        
        # Add new participant
        await self.collection.update_one(
            {"_id": ObjectId(raffle_id)},
            {
                "$push": {"participants": participant.dict()},
                "$inc": {"totalParticipants": 1},
                "$set": {"updatedAt": datetime.now()}
            }
        )
        
        return await self.get_by_id(raffle_id)

    async def draw_winners(self, raffle_id: str, draw_model: DrawWinnersModel) -> Optional[RaffleModel]:
        """
        Draw winners for a raffle
        """
        if not ObjectId.is_valid(raffle_id):
            return None
        
        # Get the raffle
        raffle = await self.get_by_id(raffle_id)
        if not raffle:
            return None
        
        # Determine number of winners to draw
        num_to_draw = draw_model.count if draw_model.count is not None else raffle.numWinners
        
        # Make sure we don't try to draw more winners than there are participants
        num_to_draw = min(num_to_draw, len(raffle.participants))
        
        if num_to_draw <= 0:
            # No participants or already all winners drawn
            return raffle
        
        # Get all participant IDs who are not already winners
        existing_winner_ids = [w.userId for w in raffle.winners]
        eligible_participants = [p for p in raffle.participants if p.userId not in existing_winner_ids]
        
        if not eligible_participants:
            # No eligible participants left
            return raffle
        
        # Randomly select winners
        num_to_draw = min(num_to_draw, len(eligible_participants))
        selected_winners = random.sample(eligible_participants, num_to_draw)
        
        # Add winners to the raffle
        for winner in selected_winners:
            await self.collection.update_one(
                {"_id": ObjectId(raffle_id)},
                {
                    "$push": {"winners": {"userId": winner.userId}},
                    "$set": {"updatedAt": datetime.now()}
                }
            )
        
        # Mark raffle as expired if all winners have been drawn
        raffle = await self.get_by_id(raffle_id)
        if len(raffle.winners) >= raffle.numWinners:
            await self.collection.update_one(
                {"_id": ObjectId(raffle_id)},
                {"$set": {"isExpired": True, "updatedAt": datetime.now()}}
            )
        
        return await self.get_by_id(raffle_id)

    async def expire_raffle(self, raffle_id: str) -> Optional[RaffleModel]:
        """
        Mark a raffle as expired
        """
        if not ObjectId.is_valid(raffle_id):
            return None
        
        await self.collection.update_one(
            {"_id": ObjectId(raffle_id)},
            {"$set": {"isExpired": True, "updatedAt": datetime.now()}}
        )
        
        return await self.get_by_id(raffle_id)

    async def get_all_with_filters(
        self, 
        filter_params: RaffleFilter,
        pagination: PaginationParams
    ) -> Tuple[List[RaffleModel], int]:
        """
        Get all raffles with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.guildId:
            query["guildId"] = filter_params.guildId
            
        if filter_params.isExpired is not None:
            query["isExpired"] = filter_params.isExpired
            
        if filter_params.chain:
            query["chain"] = filter_params.chain
            
        if filter_params.created_after:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$gte"] = filter_params.created_after
            
        if filter_params.created_before:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$lte"] = filter_params.created_before
            
        if filter_params.has_winners is not None:
            if filter_params.has_winners:
                query["winners"] = {"$exists": True, "$not": {"$size": 0}}
            else:
                query["winners"] = {"$exists": True, "$size": 0}
                
        if filter_params.entry_cost_min is not None:
            query["entryCost"] = query.get("entryCost", {})
            query["entryCost"]["$gte"] = filter_params.entry_cost_min
            
        if filter_params.entry_cost_max is not None:
            query["entryCost"] = query.get("entryCost", {})
            query["entryCost"]["$lte"] = filter_params.entry_cost_max
        
        # Count total documents matching the query
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        raffles = []
        async for raffle_doc in cursor:
            raffles.append(RaffleModel(**raffle_doc))
        
        return raffles, total

    async def search(self, query_string: str, pagination: PaginationParams) -> Tuple[List[RaffleModel], int]:
        """
        Search raffles by a general query string
        """
        # Building a search query across multiple fields
        query = {
            "$or": [
                {"raffleTitle": {"$regex": query_string, "$options": "i"}},
                {"description": {"$regex": query_string, "$options": "i"}},
                {"partnerTwitter": {"$regex": query_string, "$options": "i"}},
                {"guildId": {"$regex": query_string, "$options": "i"}},
                {"chain": {"$regex": query_string, "$options": "i"}},
            ]
        }
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        raffles = []
        async for raffle_doc in cursor:
            raffles.append(RaffleModel(**raffle_doc))
        
        return raffles, total
    
    async def get_raffle_analytics(self) -> RaffleAnalytics:
        """
        Get analytics for all raffles
        """
        # Count total raffles
        total_raffles = await self.collection.count_documents({})
        
        # Count active and expired raffles
        active_raffles = await self.collection.count_documents({"isExpired": False})
        expired_raffles = await self.collection.count_documents({"isExpired": True})
        
        # Aggregate raffles by guild
        guild_pipeline = [
            {"$group": {"_id": "$guildId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        guild_results = await self.collection.aggregate(guild_pipeline).to_list(length=None)
        raffles_by_guild = {item["_id"]: item["count"] for item in guild_results}
        
        # Aggregate raffles by chain
        chain_pipeline = [
            {"$group": {"_id": "$chain", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        chain_results = await self.collection.aggregate(chain_pipeline).to_list(length=None)
        raffles_by_chain = {item["_id"]: item["count"] for item in chain_results}
        
        # Calculate total participants across all raffles
        total_participants_pipeline = [
            {"$group": {"_id": None, "totalParticipants": {"$sum": "$totalParticipants"}}}
        ]
        participants_result = await self.collection.aggregate(total_participants_pipeline).to_list(length=None)
        total_participants = participants_result[0]["totalParticipants"] if participants_result else 0
        
        # Calculate total entry points spent
        total_entry_pipeline = [
            {"$project": {"totalEntryValue": {"$multiply": ["$entryCost", "$totalParticipants"]}}}
        ]
        entry_results = await self.collection.aggregate(total_entry_pipeline).to_list(length=None)
        total_entry_points = sum(result.get("totalEntryValue", 0) for result in entry_results)
        
        # Get top raffles by participation
        top_raffles_pipeline = [
            {"$sort": {"totalParticipants": -1}},
            {"$limit": 5},
            {"$project": {
                "_id": 1,
                "raffleTitle": 1,
                "totalParticipants": 1,
                "entryCost": 1,
                "totalEntryValue": {"$multiply": ["$entryCost", "$totalParticipants"]}
            }}
        ]
        top_raffles_result = await self.collection.aggregate(top_raffles_pipeline).to_list(length=None)
        
        top_raffles = []
        for raffle in top_raffles_result:
            top_raffles.append(RaffleStatistics(
                raffle_id=str(raffle["_id"]),
                title=raffle["raffleTitle"],
                total_participants=raffle["totalParticipants"],
                entry_cost=raffle["entryCost"],
                total_entry_value=raffle["totalEntryValue"]
            ))
        
        return RaffleAnalytics(
            total_raffles=total_raffles,
            active_raffles=active_raffles,
            expired_raffles=expired_raffles,
            total_participants=total_participants,
            total_entry_points_spent=total_entry_points,
            raffles_by_guild=raffles_by_guild,
            top_raffles=top_raffles,
            raffles_by_chain=raffles_by_chain
        )