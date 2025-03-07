from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorCursor
from datetime import datetime
from bson import ObjectId

from ...models.guild import GuildModel, GuildCreate, GuildUpdate, GuildFilter
from ...models.user import PaginationParams

class GuildRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.guilds

    async def create(self, guild: GuildCreate) -> GuildModel:
        """
        Create a new guild in the database
        """
        guild_data = guild.dict()
        guild_data["createdAt"] = datetime.now()
        guild_data["updatedAt"] = datetime.now()
        
        result = await self.collection.insert_one(guild_data)
        guild_data["_id"] = result.inserted_id
        
        return GuildModel(**guild_data)

    async def get_by_id(self, guild_id: str) -> Optional[GuildModel]:
        """
        Get a guild by MongoDB ID
        """
        if not ObjectId.is_valid(guild_id):
            return None
            
        guild = await self.collection.find_one({"_id": ObjectId(guild_id)})
        if guild:
            return GuildModel(**guild)
        return None

    async def get_by_guild_id(self, discord_guild_id: str) -> Optional[GuildModel]:
        """
        Get a guild by Discord Guild ID
        """
        guild = await self.collection.find_one({"guildId": discord_guild_id})
        if guild:
            return GuildModel(**guild)
        return None

    async def update(self, guild_id: str, guild_update: GuildUpdate) -> Optional[GuildModel]:
        """
        Update a guild
        """
        if not ObjectId.is_valid(guild_id):
            return None
            
        update_data = guild_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(guild_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(guild_id)

    async def delete(self, guild_id: str) -> bool:
        """
        Delete a guild
        """
        if not ObjectId.is_valid(guild_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(guild_id)})
        return result.deleted_count > 0

    async def get_all_with_filters(
        self, 
        filter_params: GuildFilter,
        pagination: PaginationParams
    ) -> Tuple[List[GuildModel], int]:
        """
        Get all guilds with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.subscription_tier:
            query["subscription.tier"] = filter_params.subscription_tier
            
        if filter_params.category:
            query["category"] = filter_params.category
            
        if filter_params.user_category:
            query["userCategory"] = filter_params.user_category
            
        if filter_params.rating:
            query["analytics.rating"] = filter_params.rating
            
        if filter_params.is_top10 is not None:
            query["analytics.isTop10"] = filter_params.is_top10
            
        if filter_params.bot_enabled is not None:
            query["botConfig.enabled"] = filter_params.bot_enabled
            
        if filter_params.owner_discord_id:
            query["ownerDiscordId"] = filter_params.owner_discord_id
            
        if filter_params.created_after:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$gte"] = filter_params.created_after
            
        if filter_params.created_before:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$lte"] = filter_params.created_before
        
        # Count total documents matching the query
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        guilds = []
        async for guild_doc in cursor:
            guilds.append(GuildModel(**guild_doc))
        
        return guilds, total

    async def search(self, query_string: str, pagination: PaginationParams) -> Tuple[List[GuildModel], int]:
        """
        Search guilds by a general query string
        """
        # Building a search query across multiple fields
        query = {
            "$or": [
                {"guildName": {"$regex": query_string, "$options": "i"}},
                {"guildId": {"$regex": query_string, "$options": "i"}},
                {"ownerDiscordId": {"$regex": query_string, "$options": "i"}},
                {"category": {"$regex": query_string, "$options": "i"}},
                {"userCategory": {"$regex": query_string, "$options": "i"}},
                {"twitterUrl": {"$regex": query_string, "$options": "i"}},
            ]
        }
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        guilds = []
        async for guild_doc in cursor:
            guilds.append(GuildModel(**guild_doc))
        
        return guilds, total
    
    async def get_guild_analytics(self) -> Dict[str, Any]:
        """
        Get analytics for all guilds
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$subscription.tier", 
                    "count": {"$sum": 1},
                    "avgActiveUsers": {"$avg": "$analytics.metrics.activeUsers"},
                    "avgMessageCount": {"$avg": "$analytics.metrics.messageCount"},
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=None)
        
        # Count guilds by category
        categories = await self.collection.aggregate([
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]).to_list(length=None)
        
        # Count guilds by rating
        ratings = await self.collection.aggregate([
            {"$group": {"_id": "$analytics.rating", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]).to_list(length=None)
        
        return {
            "subscription_tiers": result,
            "categories": categories,
            "ratings": ratings,
            "total_guilds": await self.collection.count_documents({}),
            "active_bots": await self.collection.count_documents({"botConfig.enabled": True})
        }