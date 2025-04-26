import stripe
from typing import Dict, Any, Optional, List, Tuple
from fastapi import HTTPException, status
from datetime import datetime

from ..config import settings
from ..models.guild_subscription import (
    GuildSubscriptionTier, 
    StripeGuildSubscriptionDetails, 
    GuildSubscription,
    GuildSubscriptionResponse
)
from ..models.guild import GuildModel
from ..models.user import UserModel

# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_API_KEY

class GuildStripeService:
    @staticmethod
    async def get_guild_subscription_prices(tier: GuildSubscriptionTier) -> List[Dict[str, Any]]:
        """
        Get all available prices for a specific guild subscription tier
        """        
        try:
            # Get all active products
            products = stripe.Product.list(active=True)
            
            # Find products matching the tier name
            tier_products = []
            for product in products.data:
                product_name = product.name.lower()
                if tier.value in product_name:
                    tier_products.append(product)
            
            if not tier_products:
                return []
            
            # Get all prices for these products
            all_prices = []
            for product in tier_products:
                prices = stripe.Price.list(
                    active=True,
                    product=product.id
                )
                
                for price in prices.data:
                    if price.recurring:
                        price_data = {
                            "price_id": price.id,
                            "product_id": product.id,
                            "product_name": product.name,
                            "amount": price.unit_amount / 100.0,
                            "currency": price.currency,
                            "interval": price.recurring.interval,
                            "interval_count": price.recurring.interval_count,
                            "nickname": price.nickname
                        }
                        all_prices.append(price_data)
            
            return all_prices
        
        except stripe.error.StripeError as e:
            print(f"Stripe error fetching prices: {str(e)}")
            return []

    @staticmethod
    async def find_price_id(
        tier: GuildSubscriptionTier, 
        interval: Optional[str] = None, 
        interval_count: Optional[int] = None
    ) -> Optional[str]:
        """
        Find a price ID for a specific tier and interval
        """
        prices = await GuildStripeService.get_guild_subscription_prices(tier)
        
        if not prices:
            return None
        
        # If interval is specified, filter by it
        if interval:
            filtered_prices = [p for p in prices if p["interval"] == interval]
            
            # Further filter by interval_count if specified
            if interval_count and filtered_prices:
                filtered_prices = [p for p in filtered_prices if p["interval_count"] == interval_count]
            
            if filtered_prices:
                # Sort by amount and return the first (cheapest) price
                filtered_prices.sort(key=lambda x: x["amount"])
                return filtered_prices[0]["price_id"]
        
        # If no interval specified or no matches found, return the cheapest monthly price
        monthly_prices = [p for p in prices if p["interval"] == "month" and p["interval_count"] == 1]
        if monthly_prices:
            monthly_prices.sort(key=lambda x: x["amount"])
            return monthly_prices[0]["price_id"]
        
        # If no monthly price, return any price
        prices.sort(key=lambda x: x["amount"])
        return prices[0]["price_id"] if prices else None

    @staticmethod
    async def get_or_create_customer(user: UserModel, guild_id: str, guild_repository=None) -> str:
        """
        Get existing Stripe customer ID or create a new one for the guild
        """        
        # First, check if guild exists and has a Stripe customer ID
        guild = None
        if guild_repository:
            guild = await guild_repository.get_by_guild_id(guild_id)

        if guild and guild.subscription and hasattr(guild.subscription, 'stripe') and guild.subscription.stripe and guild.subscription.stripe.stripe_customer_id:
            customer_id = guild.subscription.stripe.stripe_customer_id
            return customer_id
        
        # Create a new customer in Stripe
        try:            
            # Get guild name if we have the guild object, otherwise use the ID
            guild_name = guild.guildName if guild else f"Guild {guild_id}"
            
            customer = stripe.Customer.create(
                email=f"{guild_id}@discord.guild",
                name=guild_name,
                metadata={
                    "guild_id": guild_id,
                    "owner_discord_id": user.discordId,
                    "user_id": str(user.id)
                }
            )
            customer_id = customer.id
            
            # Update the guild in the database with the new Stripe customer ID
            if guild_repository and guild:
                
                # Create or update the subscription object
                stripe_details = StripeGuildSubscriptionDetails(stripe_customer_id=customer_id)
                
                # Convert existing subscription
                if hasattr(guild.subscription, 'tier'):
                    # If it's already an GuildSubscription
                    subscription = guild.subscription
                    if not hasattr(subscription, 'stripe') or not subscription.stripe:
                        subscription.stripe = stripe_details
                    else:
                        subscription.stripe.stripe_customer_id = customer_id
                else:
                    # If it's the old GuildSubscription format
                    subscription = GuildSubscription(
                        tier=GuildSubscriptionTier(guild.subscription.tier) if hasattr(guild.subscription, 'tier') else GuildSubscriptionTier.FREE,
                        startDate=guild.subscription.startDate if hasattr(guild.subscription, 'startDate') else None,
                        endDate=guild.subscription.endDate if hasattr(guild.subscription, 'endDate') else None,
                        autoRenew=guild.subscription.autoRenew if hasattr(guild.subscription, 'autoRenew') else True,
                        stripe=stripe_details
                    )
                
                # Update the guild
                from ..models.guild import GuildUpdate
                update_data = GuildUpdate(subscription=subscription)
                
                try:
                    await guild_repository.update(str(guild.id), update_data)
                except Exception as e:
                    print(f"Error updating guild with Stripe customer ID: {str(e)}")
            
            return customer_id
        except stripe.error.StripeError as e:
            print(f"Stripe error creating customer: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Stripe customer: {str(e)}"
            )

    @staticmethod
    async def create_guild_checkout_session(
        user: UserModel,
        guild_id: str,
        tier: GuildSubscriptionTier,
        price_id: Optional[str] = None,
        interval: Optional[str] = None,
        interval_count: Optional[int] = None,
        success_url: str = None,
        cancel_url: str = None,
        guild_repository=None
    ) -> Dict[str, str]:
        """
        Create a Stripe Checkout session for guild subscription purchase
        """        
        if tier == GuildSubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create checkout session for free tier"
            )
            
        # Determine price ID to use
        if not price_id:
            price_id = await GuildStripeService.find_price_id(tier, interval, interval_count)
                    
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No price found for subscription tier: {tier}"
            )
            
        # Get or create Stripe customer
        try:
            customer_id = await GuildStripeService.get_or_create_customer(user, guild_id, guild_repository)
        except Exception as e:
            print(f"Error getting/creating Stripe customer: {str(e)}")
            raise
        
        # Create the checkout session
        try:
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
                    "guild_id": guild_id,
                    "tier": tier.value,
                    "price_id": price_id,
                    "user_id": str(user.id),
                    "entity_type": "guild"  # Indicate this is a guild subscription
                },
                allow_promotion_codes="true",
            )
            
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
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
    def convert_stripe_subscription_to_guild_format(subscription: Dict[str, Any]) -> StripeGuildSubscriptionDetails:
        """
        Convert a Stripe subscription object to our Guild DB model format
        """        
        # Extract interval information
        interval = None
        interval_count = None
        price_id = None
        
        if subscription.get("items", {}).get("data"):
            price_data = subscription.get("items", {}).get("data")[0].get("price", {})
            price_id = price_data.get("id")
            
            recurring = price_data.get("recurring", {})
            if recurring:
                interval = recurring.get("interval")
                interval_count = recurring.get("interval_count", 1)
        
        # Extract metadata if available
        metadata = subscription.get("metadata", {})
        
        # Use metadata interval/count if available and not found in price data
        if not interval and "interval" in metadata:
            interval = metadata.get("interval")
            
        if not interval_count and "interval_count" in metadata:
            try:
                interval_count = int(metadata.get("interval_count"))
            except (ValueError, TypeError):
                pass
        
        # If price_id not found in items, check metadata
        if not price_id and "price_id" in metadata:
            price_id = metadata.get("price_id")
        
        # Create with all available data
        return StripeGuildSubscriptionDetails(
            stripe_customer_id=subscription.get("customer"),
            stripe_subscription_id=subscription.get("id"),
            stripe_price_id=price_id,
            status=subscription.get("status"),
            current_period_start=datetime.fromtimestamp(subscription.get("current_period_start")) if subscription.get("current_period_start") else datetime.now(),
            current_period_end=datetime.fromtimestamp(subscription.get("current_period_end")) if subscription.get("current_period_end") else None,
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            canceled_at=datetime.fromtimestamp(subscription.get("canceled_at")) if subscription.get("canceled_at") else None,
            payment_method_id=subscription.get("default_payment_method"),
            interval=interval,
            interval_count=interval_count
        )
        
    @staticmethod
    async def get_tier_from_price_id(price_id: str) -> GuildSubscriptionTier:
        """
        Get the subscription tier from a Stripe price ID
        """        
        try:
            # Get the price to find its product
            price = stripe.Price.retrieve(price_id)
            product_id = price.product
            
            # Get the product to determine the tier
            product = stripe.Product.retrieve(product_id)
            product_name = product.name.lower()
            
            # Match tier based on product name
            if "seed" in product_name:
                return GuildSubscriptionTier.SEED
            elif "flare" in product_name:
                return GuildSubscriptionTier.FLARE
            elif "titan" in product_name:
                return GuildSubscriptionTier.TITAN
            else:
                return GuildSubscriptionTier.FREE
                
        except stripe.error.StripeError as e:
            print(f"Error retrieving product for price: {str(e)}")
            return GuildSubscriptionTier.FREE
        
    @staticmethod
    async def cancel_guild_subscription(
        guild: GuildModel, 
        at_period_end: bool = True
    ) -> StripeGuildSubscriptionDetails:
        """
        Cancel a Stripe subscription for a guild
        """        
        if (not guild.subscription or 
            not hasattr(guild.subscription, 'stripe') or 
            not guild.subscription.stripe or 
            not guild.subscription.stripe.stripe_subscription_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guild does not have an active subscription"
            )
            
        try:
            subscription_id = guild.subscription.stripe.stripe_subscription_id
            
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=at_period_end
            )
            
            # If immediate cancellation is requested, cancel right away
            if not at_period_end:
                subscription = stripe.Subscription.delete(subscription_id)
            
            # Update subscription details
            stripe_details = GuildStripeService.convert_stripe_subscription_to_guild_format(subscription)
            
            return stripe_details
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel subscription: {str(e)}"
            )
        
    @staticmethod
    async def create_guild_portal_session(
        guild: GuildModel, 
        return_url: str
    ) -> str:
        """
        Create a Stripe Customer Portal session for managing guild subscription
        """        
        if (not guild.subscription or 
            not hasattr(guild.subscription, 'stripe') or 
            not guild.subscription.stripe or 
            not guild.subscription.stripe.stripe_customer_id):
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guild does not have a Stripe customer account"
            )
            
        try:
            customer_id = guild.subscription.stripe.stripe_customer_id
            
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            
            return session.url
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create customer portal session: {str(e)}"
            )