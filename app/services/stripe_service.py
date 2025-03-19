import stripe
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from datetime import datetime

from ..config import settings
from ..models.subscription import (
    SubscriptionTier, 
    StripeSubscriptionDetails, 
    EnhancedSubscription, 
    SubscriptionStatus,
    CheckoutSessionResponse
)
from ..models.user import UserModel

# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_API_KEY

# Mapping of subscription tiers to Stripe price IDs
# These should match your actual Stripe price IDs
TIER_TO_PRICE_ID = {
    SubscriptionTier.FREE: None,  # Free tier doesn't have a price ID
    # Monthly pricing
    SubscriptionTier.SEED: "price_1R2gOBPppmUobcNQSyO8qnHZ",
    SubscriptionTier.INDIVIDUAL: "price_1R2gP4PppmUobcNQGXvNlju3",
    SubscriptionTier.FLARE: "price_1R2gIaPppmUobcNQYQrhw3NT",
    SubscriptionTier.TITAN: "price_1R2gLzPppmUobcNQyWYhP6xp",
    SubscriptionTier.HYPERIUM: "price_1R2gDyPppmUobcNQ6R5CYNUl",
}


class StripeService:
    @staticmethod
    async def get_or_create_customer(user: UserModel, user_repository=None) -> str:
        """
        Get existing Stripe customer ID or create a new one for the user
        """
        print(f"Getting or creating Stripe customer for user: {user.discordUsername} (ID: {user.id})")
        
        # Check if user already has a Stripe customer ID
        if user.subscription and user.subscription.stripe and user.subscription.stripe.stripe_customer_id:
            customer_id = user.subscription.stripe.stripe_customer_id
            print(f"User already has Stripe customer ID: {customer_id}")
            return customer_id
        
        # Create a new customer in Stripe
        try:
            print(f"Creating new Stripe customer for user")
            customer = stripe.Customer.create(
                email=f"{user.discordUsername}@discord.id",
                name=user.discordUsername,
                metadata={
                    "discord_id": user.discordId,
                    "user_id": str(user.id)
                }
            )
            customer_id = customer.id
            print(f"Created new Stripe customer with ID: {customer_id}")
            
            # Update the user in the database with the new Stripe customer ID
            if user_repository:
                print(f"Updating user record with Stripe customer ID")
                
                # Create or update the subscription object
                if not user.subscription:
                    from ..models.subscription import EnhancedSubscription, StripeSubscriptionDetails
                    stripe_details = StripeSubscriptionDetails(stripe_customer_id=customer_id)
                    subscription = EnhancedSubscription(stripe=stripe_details)
                else:
                    subscription = user.subscription
                    if not subscription.stripe:
                        from ..models.subscription import StripeSubscriptionDetails
                        subscription.stripe = StripeSubscriptionDetails(stripe_customer_id=customer_id)
                    else:
                        subscription.stripe.stripe_customer_id = customer_id
                
                # Update the user
                from ..models.user import UserUpdate
                update_data = UserUpdate(subscription=subscription)
                
                try:
                    await user_repository.update(str(user.id), update_data)
                    print(f"Successfully updated user with Stripe customer ID")
                except Exception as e:
                    print(f"Error updating user with Stripe customer ID: {str(e)}")
                    # Continue anyway, as we at least have the customer created in Stripe
            else:
                print(f"Warning: No user_repository provided, cannot update user record")
            
            return customer_id
        except stripe.error.StripeError as e:
            print(f"Stripe error creating customer: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Stripe customer: {str(e)}"
            )

    @staticmethod
    async def create_checkout_session(
        user: UserModel, 
        tier: SubscriptionTier, 
        success_url: str,
        cancel_url: str,
        user_repository=None
    ) -> CheckoutSessionResponse:
        """
        Create a Stripe Checkout session for subscription purchase
        """
        print(f"Creating checkout session for user: {user.discordUsername} (ID: {user.id})")
        print(f"Requested tier: {tier}")
        
        if tier == SubscriptionTier.FREE:
            print("Cannot create checkout for free tier")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create checkout session for free tier"
            )
            
        # Get price ID for the requested tier
        price_id = TIER_TO_PRICE_ID.get(tier)
        print(f"Mapped price ID for tier {tier}: {price_id}")
        
        if not price_id:
            print(f"No price ID found for tier: {tier}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subscription tier: {tier}"
            )
            
        # Get or create Stripe customer
        try:
            customer_id = await StripeService.get_or_create_customer(user, user_repository)
            print(f"Using Stripe customer ID: {customer_id}")
        except Exception as e:
            print(f"Error getting/creating Stripe customer: {str(e)}")
            raise
        
        # Create the checkout session
        try:
            print(f"Creating Stripe checkout session with price ID: {price_id}")
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "discord_id": user.discordId,
                    "tier": tier.value
                }
            )
            
            print(f"Checkout session created successfully: {session.id}")
            print(f"Session URL: {session.url}")
            
            return CheckoutSessionResponse(
                checkout_url=session.url,
                session_id=session.id
            )
        except stripe.error.StripeError as e:
            print(f"Stripe error creating checkout session: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create checkout session: {str(e)}"
            )
        except Exception as e:
            print(f"Unexpected error creating checkout session: {str(e)}")
            raise

    @staticmethod
    async def create_customer_portal_session(
        user: UserModel, 
        return_url: str
    ) -> str:
        """
        Create a Stripe Customer Portal session for managing subscription
        """
        if not user.subscription or not user.subscription.stripe or not user.subscription.stripe.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have a Stripe customer ID"
            )
            
        try:
            session = stripe.billing_portal.Session.create(
                customer=user.subscription.stripe.stripe_customer_id,
                return_url=return_url
            )
            return session.url
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create customer portal session: {str(e)}"
            )

    @staticmethod
    async def cancel_subscription(
        user: UserModel, 
        at_period_end: bool = True
    ) -> StripeSubscriptionDetails:
        """
        Cancel a Stripe subscription
        """
        if not user.subscription or not user.subscription.stripe or not user.subscription.stripe.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have an active subscription"
            )
            
        try:
            subscription = stripe.Subscription.modify(
                user.subscription.stripe.stripe_subscription_id,
                cancel_at_period_end=at_period_end
            )
            
            # Update subscription details
            stripe_details = StripeSubscriptionDetails(
                stripe_customer_id=subscription.customer,
                stripe_subscription_id=subscription.id,
                stripe_price_id=subscription.items.data[0].price.id if subscription.items.data else None,
                status=SubscriptionStatus(subscription.status),
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end),
                cancel_at_period_end=subscription.cancel_at_period_end,
                canceled_at=datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None,
                payment_method_id=subscription.default_payment_method
            )
            
            return stripe_details
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel subscription: {str(e)}"
            )

    # @staticmethod
    # def convert_stripe_subscription_to_db_format(subscription: Dict[str, Any]) -> StripeSubscriptionDetails:
    #     """
    #     Convert a Stripe subscription object to our DB model format
    #     """
    #     return StripeSubscriptionDetails(
    #         stripe_customer_id=subscription.get("customer"),
    #         stripe_subscription_id=subscription.get("id"),
    #         stripe_price_id=subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id") if subscription.get("items", {}).get("data") else None,
    #         status=SubscriptionStatus(subscription.get("status")),
    #         current_period_start=datetime.fromtimestamp(subscription.get("current_period_start")) if subscription.get("current_period_start") else None,
    #         current_period_end=datetime.fromtimestamp(subscription.get("current_period_end")) if subscription.get("current_period_end") else None,
    #         cancel_at_period_end=subscription.get("cancel_at_period_end", False),
    #         canceled_at=datetime.fromtimestamp(subscription.get("canceled_at")) if subscription.get("canceled_at") else None,
    #         payment_method_id=subscription.get("default_payment_method")
    #     )
        
    # @staticmethod
    # def get_tier_from_price_id(price_id: str) -> SubscriptionTier:
    #     """
    #     Get the subscription tier from a Stripe price ID
    #     """
    #     for tier, tier_price_id in TIER_TO_PRICE_ID.items():
    #         if tier_price_id == price_id:
    #             return tier
    #     return SubscriptionTier.FREE  # Default to free if price ID not found

    # Add debug statements to the StripeService methods

    @staticmethod
    def convert_stripe_subscription_to_db_format(subscription: Dict[str, Any]) -> StripeSubscriptionDetails:
        """
        Convert a Stripe subscription object to our DB model format
        """
        print(f"Converting Stripe subscription to DB format. Subscription ID: {subscription.get('id')}")
        
        # Log critical parts of the subscription object
        print(f"  Customer ID: {subscription.get('customer')}")
        print(f"  Status: {subscription.get('status')}")
        print(f"  Current period: {subscription.get('current_period_start')} to {subscription.get('current_period_end')}")
        
        # Extract price ID
        price_id = None
        if subscription.get("items", {}).get("data"):
            price_id = subscription.get("items", {}).get("data")[0].get("price", {}).get("id")
        print(f"  Price ID: {price_id}")
        
        return StripeSubscriptionDetails(
            stripe_customer_id=subscription.get("customer"),
            stripe_subscription_id=subscription.get("id"),
            stripe_price_id=price_id,
            status=SubscriptionStatus(subscription.get("status")),
            current_period_start=datetime.fromtimestamp(subscription.get("current_period_start")) if subscription.get("current_period_start") else None,
            current_period_end=datetime.fromtimestamp(subscription.get("current_period_end")) if subscription.get("current_period_end") else None,
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            canceled_at=datetime.fromtimestamp(subscription.get("canceled_at")) if subscription.get("canceled_at") else None,
            payment_method_id=subscription.get("default_payment_method")
        )

    @staticmethod
    def get_tier_from_price_id(price_id: str) -> SubscriptionTier:
        """
        Get the subscription tier from a Stripe price ID
        """
        print(f"Looking up tier for price ID: {price_id}")
        
        # Print the entire mapping for debugging
        print(f"TIER_TO_PRICE_ID mapping: {TIER_TO_PRICE_ID}")
        
        # Check for direct match
        for tier, tier_price_id in TIER_TO_PRICE_ID.items():
            if tier_price_id == price_id:
                print(f"Found direct match: {tier}")
                return tier
        
        # If no direct match, try to identify tier from price ID string
        price_id_lower = price_id.lower()
        if "individual" in price_id_lower:
            print(f"Matched tier by name: INDIVIDUAL")
            return SubscriptionTier.INDIVIDUAL
        elif "hyperium" in price_id_lower:
            print(f"Matched tier by name: HYPERIUM")
            return SubscriptionTier.HYPERIUM
        elif "titan" in price_id_lower:
            print(f"Matched tier by name: TITAN")
            return SubscriptionTier.TITAN
        elif "flare" in price_id_lower:
            print(f"Matched tier by name: FLARE")
            return SubscriptionTier.FLARE
        elif "seed" in price_id_lower:
            print(f"Matched tier by name: SEED")
            return SubscriptionTier.SEED
        
        # Default to free if price ID not found
        print(f"No tier match found, defaulting to FREE")
        return SubscriptionTier.FREE