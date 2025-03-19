from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.subscriptions import SubscriptionRepository
from ..db.repositories.users import UserRepository
from ..models.subscription import (
    SubscriptionTier, 
    Subscription, 
    StripeSubscriptionDetails,
    SubscriptionStatus,
    CheckoutSessionResponse
)
from ..models.user import UserModel, UserUpdate
from .stripe_service import StripeService


class SubscriptionService:
    def __init__(
        self, 
        subscription_repository: SubscriptionRepository,
        user_repository: UserRepository
    ):
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository

    async def create_checkout_session(
        self, 
        user: UserModel, 
        tier: SubscriptionTier, 
        success_url: str,
        cancel_url: str
    ) -> CheckoutSessionResponse:
        """
        Create a checkout session for a subscription
        """
        return await StripeService.create_checkout_session(
            user, 
            tier, 
            success_url, 
            cancel_url,
            self.user_repository
        )

    async def create_customer_portal_session(
        self, 
        user: UserModel, 
        return_url: str
    ) -> str:
        """
        Create a customer portal session for subscription management
        """
        return await StripeService.create_customer_portal_session(user, return_url)

    async def cancel_subscription(
        self, 
        user: UserModel, 
        at_period_end: bool = True
    ) -> UserModel:
        """
        Cancel a user's subscription
        """
        # Call Stripe to cancel the subscription
        stripe_details = await StripeService.cancel_subscription(user, at_period_end)
        
        # Update the user's subscription details in the database
        await self.subscription_repository.update_stripe_subscription_details(
            str(user.id), 
            stripe_details
        )
        
        # If immediate cancellation, update subscription tier to FREE
        if not at_period_end:
            await self.subscription_repository.update_subscription_tier(
                str(user.id), 
                SubscriptionTier.FREE
            )
            
        # Get updated user
        updated_user = await self.user_repository.get_by_id(str(user.id))
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        return updated_user
    

    async def handle_subscription_created(self, subscription_data: Dict[str, Any]) -> Optional[UserModel]:
        """
        Handle a subscription.created webhook event
        """
        customer_id = subscription_data.get("customer")
        
        # Find user by Stripe customer ID
        user_data = await self.subscription_repository.find_user_by_stripe_customer_id(customer_id)
        if not user_data:
            # If no user found, try to check metadata for user_id
            metadata = subscription_data.get("metadata", {})
            user_id = metadata.get("user_id")
            
            if user_id:
                user_data = await self.user_repository.get_by_id(user_id)
        
        if not user_data:
            return None  # No matching user found
        
        # Found a user
        user_id = str(user_data.get("_id")) if user_data.get("_id") else None
        
        # Convert Stripe subscription to our format
        stripe_details = StripeService.convert_stripe_subscription_to_db_format(subscription_data)
        
        # Get the price ID to determine the subscription tier
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
                
        tier = StripeService.get_tier_from_price_id(price_id) if price_id else SubscriptionTier.FREE
        
        # Create subscription object
        enhanced_subscription = Subscription(
            tier=tier,
            stripe=stripe_details
        )
        
        # Update the user's subscription
        if user_id:
            update_success = await self.subscription_repository.update_user_subscription(user_id, enhanced_subscription)
            
            updated_user = await self.user_repository.get_by_id(user_id)
            if updated_user:
                return updated_user
            else:
                return None
        
        return None
    
    async def handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> Optional[UserModel]:
        """
        Handle a subscription.updated webhook event
        """
        subscription_id = subscription_data.get("id")
        
        # Find user by Stripe subscription ID
        user_data = await self.subscription_repository.find_user_by_stripe_subscription_id(subscription_id)
        if not user_data:
            return None  # No matching user found
        
        # Convert Stripe subscription to our format
        stripe_details = StripeService.convert_stripe_subscription_to_db_format(subscription_data)
        
        # Get the price ID to determine the subscription tier
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
        
        # Only update tier if price has changed
        user_id = str(user_data.get("_id"))
        current_user = await self.user_repository.get_by_id(user_id)
        
        if price_id and (not current_user.subscription.stripe or 
                        current_user.subscription.stripe.stripe_price_id != price_id):
            tier = StripeService.get_tier_from_price_id(price_id)
            await self.subscription_repository.update_subscription_tier(user_id, tier)
        
        # Update the Stripe subscription details
        await self.subscription_repository.update_stripe_subscription_details(user_id, stripe_details)
        
        # Check if subscription status is canceled or other inactive state
        if stripe_details.status != SubscriptionStatus.ACTIVE and stripe_details.status != SubscriptionStatus.TRIALING:
            # If subscription is no longer active, downgrade to FREE tier
            await self.subscription_repository.update_subscription_tier(user_id, SubscriptionTier.FREE)
        
        return await self.user_repository.get_by_id(user_id)
    
    async def handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> Optional[UserModel]:
        """
        Handle a subscription.deleted webhook event
        """
        subscription_id = subscription_data.get("id")
        
        # Find user by Stripe subscription ID
        user_data = await self.subscription_repository.find_user_by_stripe_subscription_id(subscription_id)
        if not user_data:
            return None  # No matching user found
        
        user_id = str(user_data.get("_id"))
        
        # Downgrade to FREE tier
        await self.subscription_repository.update_subscription_tier(user_id, SubscriptionTier.FREE)
        
        # Update the Stripe subscription details to reflect deletion
        stripe_details = StripeService.convert_stripe_subscription_to_db_format(subscription_data)
        await self.subscription_repository.update_stripe_subscription_details(user_id, stripe_details)
        
        return await self.user_repository.get_by_id(user_id)