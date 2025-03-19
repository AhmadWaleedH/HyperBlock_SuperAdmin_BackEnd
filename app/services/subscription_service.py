from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.subscriptions import SubscriptionRepository
from ..db.repositories.users import UserRepository
from ..models.subscription import (
    SubscriptionTier, 
    EnhancedSubscription, 
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
    
    # async def handle_subscription_created(self, subscription_data: Dict[str, Any]) -> Optional[UserModel]:
    #     """
    #     Handle a subscription.created webhook event
    #     """
    #     customer_id = subscription_data.get("customer")
    #     print("customer_id")
    #     print(customer_id)
    #     # Find user by Stripe customer ID
    #     user_data = await self.subscription_repository.find_user_by_stripe_customer_id(customer_id)
    #     print("user_data")
    #     print(user_data)
    #     if not user_data:
    #         # If no user found, try to check metadata for user_id
    #         metadata = subscription_data.get("metadata", {})
    #         user_id = metadata.get("user_id")
            
    #         if user_id:
    #             user_data = await self.user_repository.get_by_id(user_id)
        
    #     if not user_data:
    #         return None  # No matching user found
    #     print("got here")
    #     # Convert Stripe subscription to our format
    #     stripe_details = StripeService.convert_stripe_subscription_to_db_format(subscription_data)
    #     print("stripe_details")
    #     print(stripe_details)
    #     # Get the price ID to determine the subscription tier
    #     price_id = None
    #     if subscription_data.get("items", {}).get("data"):
    #         price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
        
    #     tier = StripeService.get_tier_from_price_id(price_id) if price_id else SubscriptionTier.FREE
        
    #     # Create enhanced subscription object
    #     enhanced_subscription = EnhancedSubscription(
    #         tier=tier,
    #         stripe=stripe_details
    #     )
        
    #     # Update the user's subscription
    #     user_id = str(user_data.get("_id")) if user_data.get("_id") else None
    #     print(user_id)
    #     if user_id:
    #         await self.subscription_repository.update_user_subscription(user_id, enhanced_subscription)
    #         return await self.user_repository.get_by_id(user_id)
        
    #     return None

    # Update the subscription_service.py methods with debug statements

    async def handle_subscription_created(self, subscription_data: Dict[str, Any]) -> Optional[UserModel]:
        """
        Handle a subscription.created webhook event
        """
        customer_id = subscription_data.get("customer")
        print(f"Processing subscription created for customer: {customer_id}")
        
        # Find user by Stripe customer ID
        user_data = await self.subscription_repository.find_user_by_stripe_customer_id(customer_id)
        if not user_data:
            print(f"No user found with Stripe customer ID: {customer_id}")
            # If no user found, try to check metadata for user_id
            metadata = subscription_data.get("metadata", {})
            print(f"Subscription metadata: {metadata}")
            user_id = metadata.get("user_id")
            
            if user_id:
                print(f"Found user_id in metadata: {user_id}")
                user_data = await self.user_repository.get_by_id(user_id)
        
        if not user_data:
            print("No matching user found, subscription cannot be assigned")
            return None  # No matching user found
        
        # Found a user
        user_id = str(user_data.get("_id")) if user_data.get("_id") else None
        print(f"Found user with ID: {user_id}")
        
        # Convert Stripe subscription to our format
        stripe_details = StripeService.convert_stripe_subscription_to_db_format(subscription_data)
        print(f"Converted Stripe subscription details: {stripe_details}")
        
        # Get the price ID to determine the subscription tier
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
        
        print(f"Price ID from subscription: {price_id}")
        
        tier = StripeService.get_tier_from_price_id(price_id) if price_id else SubscriptionTier.FREE
        print(f"Determined subscription tier: {tier}")
        
        # Create enhanced subscription object
        enhanced_subscription = EnhancedSubscription(
            tier=tier,
            stripe=stripe_details
        )
        print(f"Created enhanced subscription object with tier: {enhanced_subscription.tier}")
        
        # Update the user's subscription
        if user_id:
            print(f"Updating user {user_id} with new subscription")
            update_success = await self.subscription_repository.update_user_subscription(user_id, enhanced_subscription)
            print(f"Update success: {update_success}")
            
            updated_user = await self.user_repository.get_by_id(user_id)
            if updated_user:
                print(f"User fetched after update: {updated_user.discordUsername}")
                print(f"Updated subscription tier: {updated_user.subscription.tier}")
                return updated_user
            else:
                print(f"Failed to fetch user after update")
                return None
        
        print("No user_id available for update")
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