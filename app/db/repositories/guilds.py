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
    
    async def find_guild_by_stripe_customer_id(self, customer_id: str) -> Optional[GuildModel]:
        """
        Find a guild by its Stripe customer ID
        """        
        if not customer_id:
            return None
            
        try:
            # First try to find in subscription.stripe.stripe_customer_id (new format)
            guild_doc = await self.collection.find_one({
                "subscription.stripe.stripe_customer_id": customer_id
            })
            
            if guild_doc:                
                # Ensure all required fields are present
                if "botConfig" not in guild_doc or guild_doc["botConfig"] is None:
                    guild_doc["botConfig"] = {}
                if "pointsSystem" not in guild_doc or guild_doc["pointsSystem"] is None:
                    guild_doc["pointsSystem"] = {}
                if "counter" not in guild_doc or guild_doc["counter"] is None:
                    guild_doc["counter"] = {}
                    
                return GuildModel(**guild_doc)
                
            return None
        except Exception as e:
            print(f"Error finding guild by Stripe customer ID: {str(e)}")
            return None
        
    async def find_guild_by_stripe_subscription_id(self, subscription_id: str) -> Optional[GuildModel]:
        """
        Find a guild by its Stripe subscription ID
        """        
        if not subscription_id:
            return None
            
        try:
            # Look for the subscription ID in the subscription
            guild_doc = await self.collection.find_one({
                "subscription.stripe.stripe_subscription_id": subscription_id
            })
            
            if guild_doc:                
                # Ensure all required fields are present
                if "botConfig" not in guild_doc or guild_doc["botConfig"] is None:
                    guild_doc["botConfig"] = {}
                if "pointsSystem" not in guild_doc or guild_doc["pointsSystem"] is None:
                    guild_doc["pointsSystem"] = {}
                if "counter" not in guild_doc or guild_doc["counter"] is None:
                    guild_doc["counter"] = {}
                    
                return GuildModel(**guild_doc)
                
            return None
        except Exception as e:
            print(f"Error finding guild by Stripe subscription ID: {str(e)}")
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
    
    # Update the analytics object in the guild
    async def update_analytics(self, guild_id: str, analytics_update: Dict[str, Any]) -> Optional[GuildModel]:
        """
        Update guild analytics fields
        """
        if not ObjectId.is_valid(guild_id):
            return None
        
        update_data = {"analytics": analytics_update, "updatedAt": datetime.now()}
        
        await self.collection.update_one(
            {"_id": ObjectId(guild_id)},
            {"$set": update_data}
        )
        
        return await self.get_by_id(guild_id)

    # Update specific fields within the analytics object
    async def update_analytics_fields(self, guild_id: str, analytics_fields: Dict[str, Any]) -> Optional[GuildModel]:
        """
        Update specific fields within guild analytics while preserving other fields
        """
        if not ObjectId.is_valid(guild_id):
            return None
        
        # Create update operations for each field
        update_operations = {}
        for field, value in analytics_fields.items():
            update_operations[f"analytics.{field}"] = value
        
        # Add updatedAt field
        update_operations["updatedAt"] = datetime.now()
        
        await self.collection.update_one(
            {"_id": ObjectId(guild_id)},
            {"$set": update_operations}
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
            
        if filter_params.bot_status is not None:
            query["botStatus"] = filter_params.bot_status
            
        if filter_params.owner_discord_id:
            query["ownerDiscordId"] = filter_params.owner_discord_id
            
        if filter_params.created_after:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$gte"] = filter_params.created_after
            
        if filter_params.created_before:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$lte"] = filter_params.created_before

        if filter_params.total_members_min is not None:
            query["totalMembers"] = query.get("totalMembers", {})
            query["totalMembers"]["$gte"] = filter_params.total_members_min
            
        if filter_params.total_members_max is not None:
            query["totalMembers"] = query.get("totalMembers", {})
            query["totalMembers"]["$lte"] = filter_params.total_members_max
        
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
        Get analytics for all guilds using the new schema
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$subscription.tier", 
                    "count": {"$sum": 1},
                    "avgCAS": {"$avg": "$analytics.CAS"},
                    "avgCHS": {"$avg": "$analytics.CHS"},
                    "avgEAS": {"$avg": "$analytics.EAS"},
                    "avgCCS": {"$avg": "$analytics.CCS"},
                    "avgERC": {"$avg": "$analytics.ERC"},
                    "totalVault": {"$sum": "$analytics.vault"},
                    "totalReservedPoints": {"$sum": "$analytics.reservedPoints"}
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
        
        # Counter statistics
        counter_stats = await self.collection.aggregate([
            {
                "$group": {
                    "_id": None,
                    "avgAnnouncementCount": {"$avg": "$counter.announcementCount"},
                    "avgEventCount": {"$avg": "$counter.eventCount"},
                    "avgTotalActiveParticipants": {"$avg": "$counter.totalActiveParticipants"},
                    "avgStoreUpdateCount": {"$avg": "$counter.storeUpdateCount"},
                    "avgAuctionUpdateCount": {"$avg": "$counter.auctionUpdateCount"}
                }
            }
        ]).to_list(length=None)
        
        return {
            "subscription_tiers": result,
            "categories": categories,
            "counter_stats": counter_stats[0] if counter_stats else {},
            "total_guilds": await self.collection.count_documents({}),
            "active_bots": await self.collection.count_documents({"botConfig.enabled": True})
        }
    
    async def get_guild_top_users(self, guild_id: str, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get top users of a guild ordered by points in descending order
        
        This method queries the users collection to find all users who are members of the specified guild,
        and returns a simplified data structure with just the user info and points.
        """
        # Connect to the users collection
        users_collection = self.database.users
        
        # Build a simplified aggregation pipeline that only extracts what we need
        pipeline = [
            # Match users who are members of this guild
            {
                "$match": {
                    "serverMemberships.guildId": guild_id
                }
            },
            # Unwind the serverMemberships array to work with individual memberships
            {
                "$unwind": "$serverMemberships"
            },
            # Match only the memberships for this guild and with active status
            {
                "$match": {
                    "serverMemberships.guildId": guild_id,
                    "serverMemberships.status": "active"
                }
            },
            # Project only the fields we need for the response
            {
                "$project": {
                    "_id": 1,
                    "discordId": 1,
                    "discordUsername": 1,
                    "guildId": "$serverMemberships.guildId",
                    "points": { "$ifNull": ["$serverMemberships.points", 0] }
                }
            },
            # Sort by points in descending order
            {
                "$sort": {
                    "points": -1
                }
            },
            # Limit to the requested number of users
            {
                "$limit": limit
            }
        ]
        
        # Execute the aggregation
        cursor = users_collection.aggregate(pipeline)
        
        # Convert cursor to list
        users_data = await cursor.to_list(length=limit)
        
        # Count total matching users for this guild (for pagination info)
        total_count = await users_collection.count_documents({
            "serverMemberships.guildId": guild_id,
            "serverMemberships.status": "active"
        })
        
        return users_data, min(total_count, limit)
    
    async def get_guild_team(self, guild_id: str, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get the admin/owner team members of a guild
        
        This method queries the users collection to find all users who are admins or owners
        of the specified guild.
        """
        # Connect to the users collection
        users_collection = self.database.users
        
        # Build a pipeline to find admin/owner team members
        pipeline = [
            # Match users who are members of this guild
            {
                "$match": {
                    "serverMemberships.guildId": guild_id
                }
            },
            # Unwind the serverMemberships array to work with individual memberships
            {
                "$unwind": "$serverMemberships"
            },
            # Match only the memberships for this guild with admin or owner user type
            {
                "$match": {
                    "serverMemberships.guildId": guild_id,
                    "serverMemberships.status": "active",
                    "serverMemberships.userType": {"$in": ["admin", "owner"]}
                }
            },
            # Project only the fields we need for the response
            {
                "$project": {
                    "_id": 1,
                    "discordId": 1,
                    "discordUsername": 1,
                    "discordUserAvatarURL": 1,
                    "guildId": "$serverMemberships.guildId",
                    "userType": "$serverMemberships.userType",
                    "joinedAt": "$serverMemberships.joinedAt"
                }
            },
            # Sort by userType (owner first, then admin) and then by username
            {
                "$sort": {
                    "userType": -1,  # -1 for descending: "owner" comes before "admin"
                    "discordUsername": 1
                }
            }
        ]

        # Add limit to the pipeline
        pipeline.append({"$limit": limit})
        
        # Execute the aggregation
        cursor = users_collection.aggregate(pipeline)
        
        # Convert cursor to list
        team_data = await cursor.to_list(length=limit)
        
        # Count total team members for this guild
        total_count = len(team_data)
        
        return team_data, total_count