from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from ...models.user import UserModel, UserCreate, UserUpdate, UserFilter, PaginationParams

class UserRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.users

    async def create(self, user: UserCreate) -> UserModel:
        """
        Create a new user in the database
        """
        user_data = user.dict()
        user_data["createdAt"] = datetime.now()
        user_data["updatedAt"] = datetime.now()
        
        result = await self.collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        
        return UserModel(**user_data)

    async def get_by_id(self, user_id: str) -> Optional[UserModel]:
        """
        Get a user by ID
        """
        if not ObjectId.is_valid(user_id):
            return None
            
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if user:
            return UserModel(**user)
        return None

    async def get_by_discord_id(self, discord_id: str) -> Optional[UserModel]:
        """
        Get a user by Discord ID
        """
        user = await self.collection.find_one({"discordId": discord_id})
        if user:
            return UserModel(**user)
        return None

    async def update(self, user_id: str, user_update: UserUpdate) -> Optional[UserModel]:
        """
        Update a user
        """
        if not ObjectId.is_valid(user_id):
            return None
            
        update_data = user_update if isinstance(user_update, dict) else user_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(user_id)

    async def delete(self, user_id: str) -> bool:
        """
        Delete a user
        """
        if not ObjectId.is_valid(user_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    async def get_all_with_filters(
        self, 
        filter_params: UserFilter,
        pagination: PaginationParams
    ) -> Tuple[List[UserModel], int]:
        """
        Get all users with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.subscription_tier:
            query["subscription.tier"] = filter_params.subscription_tier
            
        if filter_params.status:
            query["status"] = filter_params.status
            
        if filter_params.wallet_type:
            query[f"mintWallets.{filter_params.wallet_type}"] = {"$exists": True, "$ne": None}
            
        if filter_params.min_points is not None:
            query["hyperBlockPoints"] = query.get("hyperBlockPoints", {})
            query["hyperBlockPoints"]["$gte"] = filter_params.min_points
            
        if filter_params.max_points is not None:
            query["hyperBlockPoints"] = query.get("hyperBlockPoints", {})
            query["hyperBlockPoints"]["$lte"] = filter_params.max_points
            
        if filter_params.discord_username:
            query["discordUsername"] = {"$regex": filter_params.discord_username, "$options": "i"}
            
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
        users = [UserModel(**user) async for user in cursor]
        
        return users, total

    async def search(self, query_string: str, pagination: PaginationParams) -> Tuple[List[UserModel], int]:
        """
        Search users by a general query string
        """
        # Building a search query across multiple fields
        query = {
            "$or": [
                {"discordUsername": {"$regex": query_string, "$options": "i"}},
                {"discordId": {"$regex": query_string, "$options": "i"}},
                {"walletAddress": {"$regex": query_string, "$options": "i"}},
                {"socials.x": {"$regex": query_string, "$options": "i"}},
                {"socials.tg": {"$regex": query_string, "$options": "i"}},
                {"socials.yt": {"$regex": query_string, "$options": "i"}},
            ]
        }
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        users = [UserModel(**user) async for user in cursor]
        
        return users, total