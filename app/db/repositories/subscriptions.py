from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any
from bson import ObjectId

from ...models.subscription import Subscription, SubscriptionTier, StripeSubscriptionDetails


class SubscriptionRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.users  # storing subscriptions in the users collection

    async def update_user_subscription(
        self, 
        user_id: str, 
        subscription_data: Subscription
    ) -> bool:
        """
        Update a user's subscription information
        """
        if not ObjectId.is_valid(user_id):
            return False
            
        # Convert to dict for MongoDB
        subscription_dict = subscription_data.dict()
        
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription": subscription_dict}}
        )
        
        return result.modified_count > 0

    async def update_stripe_subscription_details(
        self, 
        user_id: str, 
        stripe_details: StripeSubscriptionDetails
    ) -> bool:
        """
        Update just the Stripe subscription details for a user
        """
        if not ObjectId.is_valid(user_id):
            return False
            
        # Convert to dict for MongoDB
        stripe_dict = stripe_details.dict()
        
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription.stripe": stripe_dict}}
        )
        
        return result.modified_count > 0
    
    async def update_subscription_tier(
        self, 
        user_id: str, 
        tier: SubscriptionTier
    ) -> bool:
        """
        Update just the subscription tier for a user
        """
        if not ObjectId.is_valid(user_id):
            return False
            
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription.tier": tier}}
        )
        
        return result.modified_count > 0
    
    async def find_user_by_stripe_customer_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their Stripe customer ID
        """
        if not customer_id:
            return None
            
        user = await self.collection.find_one({
            "subscription.stripe.stripe_customer_id": customer_id
        })
        
        return user
    
    async def find_user_by_stripe_subscription_id(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their Stripe subscription ID
        """
        if not subscription_id:
            return None
            
        user = await self.collection.find_one({
            "subscription.stripe.stripe_subscription_id": subscription_id
        })
        
        return user