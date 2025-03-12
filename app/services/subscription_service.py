from datetime import datetime, timedelta
from fastapi import HTTPException, status
from typing import List, Dict, Any, Optional

from ..db.repositories.subscriptions import SubscriptionRepository
from ..models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionTier

class SubscriptionService:
    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    async def create_subscription(self, subscription_data: SubscriptionCreate) -> Subscription:
        """Create a new subscription"""
        # Check if subscription tier exists
        tier = await self.subscription_repository.get_tier_by_id(str(subscription_data.tier_id))
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription tier not found"
            )
        
        # Check if user already has an active subscription
        active_subscription = await self.subscription_repository.get_active_subscription_by_user(str(subscription_data.user_id))
        if active_subscription:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has an active subscription"
            )
        
        # Set end date based on billing cycle
        days_to_add = 30 if subscription_data.billing_cycle == "monthly" else 365
        end_date = datetime.now() + timedelta(days=days_to_add)
        
        # Create subscription
        subscription = await self.subscription_repository.create(subscription_data)

        print(subscription)
        print("got here")
        
        # Update end date
        # await self.subscription_repository.update(
        #     str(subscription.id),
        #     SubscriptionUpdate(end_date=end_date)
        # )
        print("returning")
        return subscription

    async def get_subscription(self, subscription_id: str) -> Subscription:
        """Get a subscription by ID"""
        subscription = await self.subscription_repository.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found"
            )
        return subscription

    async def get_user_subscriptions(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user"""
        return await self.subscription_repository.get_by_user_id(user_id)

    async def get_active_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get active subscription for a user"""
        return await self.subscription_repository.get_active_subscription_by_user(user_id)

    async def update_subscription(self, subscription_id: str, subscription_data: SubscriptionUpdate) -> Subscription:
        """Update a subscription"""
        # Check if subscription exists
        subscription = await self.subscription_repository.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found"
            )
        
        # If tier is being changed, check if new tier exists
        if subscription_data.tier_id:
            tier = await self.subscription_repository.get_tier_by_id(str(subscription_data.tier_id))
            if not tier:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New subscription tier not found"
                )
        
        # Update subscription
        updated_subscription = await self.subscription_repository.update(subscription_id, subscription_data)
        return updated_subscription

    async def cancel_subscription(self, subscription_id: str) -> Subscription:
        """Cancel a subscription"""
        # Check if subscription exists
        subscription = await self.subscription_repository.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found"
            )
        
        # Cancel subscription
        updated_subscription = await self.subscription_repository.update(
            subscription_id,
            SubscriptionUpdate(status="cancelled", auto_renew=False)
        )
        return updated_subscription

    async def activate_subscription(self, subscription_id: str, payment_token: Optional[str] = None, customer_id: Optional[str] = None) -> Subscription:
        """Activate a subscription after payment"""
        # Check if subscription exists
        subscription = await self.subscription_repository.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found"
            )
        
        # Update subscription data
        update_data = SubscriptionUpdate(
            status="active",
            payment_token=payment_token,
            cybersource_customer_id=customer_id
        )
        
        # Activate subscription
        updated_subscription = await self.subscription_repository.update(
            subscription_id,
            update_data
        )
        return updated_subscription

    async def get_subscription_tiers(self) -> List[SubscriptionTier]:
        """Get all subscription tiers"""
        return await self.subscription_repository.get_subscription_tiers()