from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from ...models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionTier
from ...models.user import PaginationParams

class SubscriptionRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.subscriptions
        self.tiers_collection = database.subscription_tiers

    async def create(self, subscription: SubscriptionCreate) -> Subscription:
        """Create a new subscription"""
        subscription_data = subscription.dict()
        subscription_data["createdAt"] = datetime.now()
        subscription_data["updatedAt"] = datetime.now()
        
        result = await self.collection.insert_one(subscription_data)
        subscription_data["_id"] = result.inserted_id
        
        return Subscription(**subscription_data)

    async def get_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID"""
        if not ObjectId.is_valid(subscription_id):
            return None
            
        subscription = await self.collection.find_one({"_id": ObjectId(subscription_id)})
        if subscription:
            return Subscription(**subscription)
        return None

    async def get_by_user_id(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user"""
        if not ObjectId.is_valid(user_id):
            return []
            
        cursor = self.collection.find({"user_id": ObjectId(user_id)})
        subscriptions = []
        async for doc in cursor:
            subscriptions.append(Subscription(**doc))
        return subscriptions

    async def get_active_subscription_by_user(self, user_id: str) -> Optional[Subscription]:
        """Get active subscription for a user"""
        if not ObjectId.is_valid(user_id):
            return None
            
        subscription = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "status": "active"
        })
        
        if subscription:
            return Subscription(**subscription)
        return None

    async def update(self, subscription_id: str, subscription_update: SubscriptionUpdate) -> Optional[Subscription]:
        """Update a subscription"""
        if not ObjectId.is_valid(subscription_id):
            return None
            
        update_data = subscription_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(subscription_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(subscription_id)

    async def get_subscription_tiers(self) -> List[SubscriptionTier]:
        """Get all subscription tiers"""
        cursor = self.tiers_collection.find()
        tiers = []
        async for doc in cursor:
            tiers.append(SubscriptionTier(**doc))
        return tiers

    async def get_tier_by_id(self, tier_id: str) -> Optional[SubscriptionTier]:
        """Get a subscription tier by ID"""
        if not ObjectId.is_valid(tier_id):
            return None
            
        tier = await self.tiers_collection.find_one({"_id": ObjectId(tier_id)})
        if tier:
            return SubscriptionTier(**tier)
        return None