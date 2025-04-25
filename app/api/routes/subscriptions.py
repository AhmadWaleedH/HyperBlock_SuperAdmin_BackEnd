from datetime import datetime
import json
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Body, Header, Query
from typing import Dict, Any, Optional

from app.api.routes.guild_subscriptions import get_guild_subscription_service
from app.db.repositories.guilds import GuildRepository
from app.services.guild_stripe_service import GuildStripeService
from app.services.guild_subscription_service import GuildSubscriptionService

from ...models.user import UserModel
from ...models.subscription import (
    SubscriptionTier, 
    SubscriptionCreate, 
    SubscriptionUpdate,
    SubscriptionResponse,
    CheckoutSessionResponse
)
from ...services.subscription_service import SubscriptionService
from ...services.user_service import UserService
from ...db.repositories.subscriptions import SubscriptionRepository
from ...db.repositories.users import UserRepository
from ...db.database import get_database
from ...config import settings
from ..dependencies import get_current_user


router = APIRouter()

async def get_subscription_service(database = Depends(get_database)):
    subscription_repository = SubscriptionRepository(database)
    user_repository = UserRepository(database)
    return SubscriptionService(subscription_repository, user_repository)

async def get_user_service(database = Depends(get_database)):
    user_repository = UserRepository(database)
    guild_repository = GuildRepository(database)
    return UserService(user_repository, guild_repository)


@router.get("/plans", response_model=Dict[str, Any])
async def get_subscription_plans():
    """
    Get all available subscription plans from Stripe
    """
    try:
        # Get all active products
        stripe.api_key = settings.STRIPE_API_KEY
        products = stripe.Product.list(active=True)
        
        # Get prices for each product
        all_prices = stripe.Price.list(active=True, expand=["data.product"])
        
        # Create a dictionary to organize prices by product and interval
        product_prices = {}
        for price in all_prices.data:
            product_id = price.product.id
            if product_id not in product_prices:
                product_prices[product_id] = {}
            
            # Group prices by interval
            interval = f"{price.recurring.interval_count}_{price.recurring.interval}" if price.recurring else "one_time"
            if interval not in product_prices[product_id]:
                product_prices[product_id][interval] = []
            
            product_prices[product_id][interval].append(price)
        
        # Format the output with product and price information
        plans = {}
        
        # Add the free tier manually as it doesn't exist in Stripe
        plans["free"] = {
            "id": "free",
            "name": "Free Tier",
            "description": "Basic features with limited access",
            "price": 0,
            "currency": "usd",
            "interval": "month",
            "features": []
        }
        
        # Map Stripe product names to tier identifiers
        name_to_tier = {
            "Seed Tier": "seed",
            "Individual": "individual",
            "Flare Tier": "flare",
            "Titan Tier": "titan",
            "Hyperium Tier": "hyperium"
        }
        
        for product in products.data:
            # Skip any product without a default price
            if not product.default_price:
                continue
                
            # Determine tier from product name
            product_name = product.name
            tier = name_to_tier.get(product_name, product_name.lower().replace(" ", "_"))
            
            # Skip if we don't have prices for this product
            if product.id not in product_prices:
                continue
                
            # Get all price options for this product
            price_options = []
            for interval, prices in product_prices[product.id].items():
                for price in prices:
                    # Format interval string
                    if price.recurring:
                        if price.recurring.interval_count == 1:
                            interval_str = price.recurring.interval
                        else:
                            interval_str = f"{price.recurring.interval_count}-{price.recurring.interval}"
                    else:
                        interval_str = "one-time"
                    
                    price_options.append({
                        "price_id": price.id,
                        "amount": price.unit_amount / 100.0,  # Convert cents to dollars
                        "currency": price.currency,
                        "interval": interval_str,
                        "nickname": price.nickname
                    })
            
            # Sort price options by amount
            price_options.sort(key=lambda x: x["amount"])
            
            # Get the monthly price if available, otherwise use the default price
            default_price = None
            monthly_prices = [p for p in price_options if p["interval"] == "month"]
            if monthly_prices:
                default_price = monthly_prices[0]
            elif price_options:
                default_price = price_options[0]
            
            if not default_price:
                continue
                
            # Format features from description
            description = product.description or ""
            feature_list = []
            
            if ":" in description:
                # If description has a colon, split features after the colon
                parts = description.split(":", 1)
                short_desc = parts[0].strip()
                if len(parts) > 1:
                    feature_text = parts[1].strip()
                    feature_list = [feat.strip() for feat in feature_text.split(",")]
            else:
                short_desc = description
            
            # Format the plan data
            plans[tier] = {
                "id": tier,
                "name": product.name,
                "description": short_desc,
                "price": default_price["amount"],
                "currency": default_price["currency"],
                "interval": default_price["interval"],
                "price_id": default_price["price_id"],
                "features": feature_list,
                "price_options": price_options  # Include all pricing options
            }
        
        return {"plans": plans}
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching subscription plans from Stripe: {str(e)}"
        )


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_current_subscription(current_user: UserModel = Depends(get_current_user)):
    """
    Get the current user's subscription details
    """
    if not current_user.subscription:
        return SubscriptionResponse(tier=SubscriptionTier.FREE)
    
    return SubscriptionResponse(
        tier=current_user.subscription.tier,
        status=current_user.subscription.stripe.status if current_user.subscription.stripe else None,
        current_period_end=current_user.subscription.stripe.current_period_end if current_user.subscription.stripe else None,
        cancel_at_period_end=current_user.subscription.stripe.cancel_at_period_end if current_user.subscription.stripe else None,
    )


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    tier: SubscriptionTier = Body(..., embed=True),
    success_url: str = Query(..., description="URL to redirect after successful payment"),
    cancel_url: str = Query(..., description="URL to redirect after cancelled payment"),
    current_user: UserModel = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a Stripe checkout session for subscription purchase
    """
    # Get fresh user data to ensure we have the latest state
    current_user = await user_service.get_user(str(current_user.id))
    
    return await subscription_service.create_checkout_session(
        current_user, 
        tier, 
        success_url, 
        cancel_url
    )


@router.post("/portal", response_model=Dict[str, str])
async def create_portal_session(
    return_url: str = Query(..., description="URL to return to after leaving the portal"),
    current_user: UserModel = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Create a Stripe customer portal session for subscription management
    """
    portal_url = await subscription_service.create_customer_portal_session(
        current_user, 
        return_url
    )
    
    return {"portal_url": portal_url}


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    at_period_end: bool = Body(True, embed=True),
    current_user: UserModel = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Cancel the current user's subscription
    """
    updated_user = await subscription_service.cancel_subscription(
        current_user, 
        at_period_end
    )
    
    return SubscriptionResponse(
        tier=updated_user.subscription.tier,
        status=updated_user.subscription.stripe.status if updated_user.subscription.stripe else None,
        current_period_end=updated_user.subscription.stripe.current_period_end if updated_user.subscription.stripe else None,
        cancel_at_period_end=updated_user.subscription.stripe.cancel_at_period_end if updated_user.subscription.stripe else None,
    )


# Helper to determine if an event is for a guild subscription
async def is_guild_subscription_event(event_object, guild_repository=None):
    """Helper to determine if an event is for a guild subscription"""
    # Check metadata for entity_type=guild or guild_id
    metadata = event_object.get("metadata", {})
    if metadata and (metadata.get("entity_type") == "guild" or metadata.get("guild_id")):
        return True, metadata.get("guild_id")
    
    # If not found in metadata, check if customer ID is associated with a guild
    customer_id = event_object.get("customer")
    if customer_id and guild_repository:
        try:
            # Look up guild by Stripe customer ID
            guild = await guild_repository.find_guild_by_stripe_customer_id(customer_id)
            if guild:
                return True, guild.guildId
        except Exception:
            pass
    
    # If subscription_id is present, try to find a guild with this subscription ID
    subscription_id = event_object.get("id") or event_object.get("subscription")
    if subscription_id and guild_repository:
        try:
            guild = await guild_repository.find_guild_by_stripe_subscription_id(subscription_id)
            if guild:
                return True, guild.guildId
        except Exception:
            pass
    
    # Check product information if available (for subscription events)
    if event_object.get("items", {}).get("data"):
        try:
            # Get the price ID
            price_id = event_object.get("items", {}).get("data")[0].get("price", {}).get("id")
            if price_id:
                # Check if this price belongs to a guild subscription tier
                from ...services.guild_stripe_service import GuildStripeService
                
                guild_price_patterns = ["flare", "titan", "seed"]
                price_id_lower = price_id.lower()
                
                if any(pattern in price_id_lower for pattern in guild_price_patterns):
                    return True, None
        except Exception:
            pass
    
    return False, None


# Handle Stripe webhook events for both user and guild subscriptions
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
    user_service: UserService = Depends(get_user_service),
    guild_subscription_service: GuildSubscriptionService = Depends(get_guild_subscription_service)
):
    """
    Handle Stripe webhook events for both user and guild subscriptions
    """
    # Get the payload and validate signature
    data = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload=data,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}"
        )
    
    # Get the event data
    event_object = event["data"]["object"]
    
    # Determine if this is a guild or user subscription event
    is_guild_subscription = False
    guild_id = None
    
    # For subscription-related events, check if it's a guild subscription
    if event["type"] in [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted"
    ]:
        is_guild_subscription, guild_id = await is_guild_subscription_event(
            event_object, 
            guild_subscription_service.guild_repository
        )
    
    if event["type"] == "checkout.session.completed":
        # Payment was successful and the subscription was created
        session_data = event_object
        session_id = session_data.get('id')
        customer_id = session_data.get('customer')
        subscription_id = session_data.get('subscription')
        
        # Extract metadata
        metadata = session_data.get('metadata', {})
        
        # For guild subscriptions
        if is_guild_subscription:
            # If we don't have a guild_id yet, try to extract from metadata
            if not guild_id:
                guild_id = metadata.get('guild_id')
            
            # If we have guild_id, we can check if the guild exists
            if guild_id:
                # Check if guild exists
                guild = await guild_subscription_service.guild_repository.get_by_guild_id(guild_id)
                
                if guild:
                    # If guild exists but doesn't have customer ID, update it
                    if (not hasattr(guild.subscription, 'stripe') or 
                        not guild.subscription.stripe or 
                        not guild.subscription.stripe.stripe_customer_id):
                        
                        # Create stripe subscription details
                        from ...models.guild_subscription import StripeGuildSubscriptionDetails, GuildSubscription, GuildSubscriptionTier
                        
                        # Get tier from metadata if available
                        tier_str = metadata.get('tier', 'free')
                        try:
                            tier = GuildSubscriptionTier(tier_str)
                        except ValueError:
                            tier = GuildSubscriptionTier.FREE
                        
                        # Get price ID from metadata if available
                        price_id = metadata.get("price_id")
                        
                        # Try to get interval information from metadata
                        interval = metadata.get("interval")
                        interval_count = metadata.get("interval_count")
                        if interval_count and isinstance(interval_count, str) and interval_count.isdigit():
                            interval_count = int(interval_count)
                        
                        # Create complete stripe details
                        if subscription_id:
                            try:
                                subscription_data = stripe.Subscription.retrieve(subscription_id)
                                stripe_details = GuildStripeService.convert_stripe_subscription_to_guild_format(subscription_data)
                            except Exception as e:
                                print(f"Error retrieving subscription: {e}")
                                stripe_details = StripeGuildSubscriptionDetails(
                                    stripe_customer_id=customer_id,
                                    stripe_subscription_id=subscription_id,
                                    stripe_price_id=price_id,
                                    status="active",
                                    current_period_start=datetime.now()
                                )
                        
                        # Create subscription
                        if hasattr(guild.subscription, 'tier'):
                            # If it already has the format
                            guild.subscription.stripe = stripe_details
                            subscription = guild.subscription
                        else:
                            # Create new subscription
                            subscription = GuildSubscription(
                                tier=tier,
                                startDate=datetime.now(),
                                autoRenew=True,
                                stripe=stripe_details
                            )
                        
                        # Update the guild
                        from ...models.guild import GuildUpdate
                        update_data = GuildUpdate(subscription=subscription)
                        
                        await guild_subscription_service.guild_repository.update(str(guild.id), update_data)
                        
                        # Try to retrieve the full subscription details from Stripe
                        try:
                            if subscription_id:
                                subscription = stripe.Subscription.retrieve(subscription_id)
                                
                                if subscription:
                                    # Update stripe details with info from Stripe
                                    stripe_details.status = subscription.status
                                    
                                    if subscription.current_period_start:
                                        stripe_details.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
                                        
                                    if subscription.current_period_end:
                                        stripe_details.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
                                        
                                    if subscription.items and subscription.items.data:
                                        item = subscription.items.data[0]
                                        if item.price and item.price.id:
                                            stripe_details.stripe_price_id = item.price.id
                                            
                                            if item.price.recurring:
                                                stripe_details.interval = item.price.recurring.interval
                                                stripe_details.interval_count = item.price.recurring.interval_count
                                    
                                    # Update the guild with the complete details
                                    guild.subscription.stripe = stripe_details
                                    
                                    update_data = GuildUpdate(subscription=guild.subscription)
                                    await guild_subscription_service.guild_repository.update(str(guild.id), update_data)
                        except Exception:
                            pass  # Silent exception handling to avoid disrupting the flow
                else:
                    # Guild doesn't exist, create it
                    # Determine tier from metadata
                    tier_str = metadata.get("tier", "free")
                    try:
                        from ...models.guild_subscription import GuildSubscriptionTier
                        tier = GuildSubscriptionTier(tier_str)
                    except ValueError:
                        tier = GuildSubscriptionTier.FREE
                    
                    # Get price ID from metadata if available
                    price_id = metadata.get("price_id")
                    
                    # Try to get interval information from metadata
                    interval = metadata.get("interval")
                    interval_count = metadata.get("interval_count")
                    if interval_count and isinstance(interval_count, str) and interval_count.isdigit():
                        interval_count = int(interval_count)
                    
                    # Create stripe details with more complete information
                    from ...models.guild_subscription import StripeGuildSubscriptionDetails, GuildSubscription
                    stripe_details = StripeGuildSubscriptionDetails(
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                        stripe_price_id=price_id,
                        status="active",
                        current_period_start=datetime.now(),
                        interval=interval,
                        interval_count=interval_count
                    )
                    
                    # Create subscription
                    enhanced_subscription = GuildSubscription(
                        tier=tier,
                        stripe=stripe_details
                    )
                    
                    # Create new guild with all required fields
                    from ...models.guild import GuildCreate, BotConfig, PointsSystem, GuildCounter
                    new_guild_data = GuildCreate(
                        guildId=guild_id,
                        guildName=f"Guild {guild_id}",
                        subscription=enhanced_subscription,
                        botConfig=BotConfig(),
                        pointsSystem=PointsSystem(),
                        counter=GuildCounter()
                    )
                    
                    try:
                        created_guild = await guild_subscription_service.guild_repository.create(new_guild_data)
                        
                        # Try to retrieve the full subscription details from Stripe
                        try:
                            if subscription_id:
                                subscription = stripe.Subscription.retrieve(subscription_id)
                                
                                if subscription:
                                    # Update stripe details with info from Stripe
                                    stripe_details.status = subscription.status
                                    
                                    if subscription.current_period_start:
                                        stripe_details.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
                                        
                                    if subscription.current_period_end:
                                        stripe_details.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
                                        
                                    if subscription.items and subscription.items.data:
                                        item = subscription.items.data[0]
                                        if item.price and item.price.id:
                                            stripe_details.stripe_price_id = item.price.id
                                            
                                            if item.price.recurring:
                                                stripe_details.interval = item.price.recurring.interval
                                                stripe_details.interval_count = item.price.recurring.interval_count
                                    
                                    # Update the guild with the complete details
                                    created_guild.subscription.stripe = stripe_details
                                    
                                    update_data = GuildUpdate(subscription=created_guild.subscription)
                                    await guild_subscription_service.guild_repository.update(str(created_guild.id), update_data)
                        except Exception:
                            pass  # Silent exception handling to avoid disrupting the flow
                    except Exception:
                        pass  # Silent exception handling to avoid disrupting the flow
        
        # For user subscriptions
        else:
            # Try to find and update the user
            if customer_id:
                # First, check if any user already has this customer ID
                user_data = await subscription_service.subscription_repository.find_user_by_stripe_customer_id(customer_id)
                
                if not user_data:
                    # If not found by customer ID, try to get from metadata
                    user_id = metadata.get('user_id')
                    
                    if user_id:
                        try:
                            # Get user by ID
                            user = await user_service.get_user(user_id)
                            
                            # Update the user with Stripe customer and subscription IDs
                            # Only if they don't already have them
                            if (not user.subscription or 
                                not user.subscription.stripe or 
                                not user.subscription.stripe.stripe_customer_id):
                                
                                # Create stripe subscription details
                                from ...models.subscription import StripeSubscriptionDetails, Subscription
                                
                                stripe_details = StripeSubscriptionDetails(
                                    stripe_customer_id=customer_id,
                                    stripe_subscription_id=subscription_id
                                )
                                
                                # Get the tier from metadata or default to FREE
                                tier_str = metadata.get('tier', 'free')
                                from ...models.subscription import SubscriptionTier
                                
                                try:
                                    tier = SubscriptionTier(tier_str)
                                except ValueError:
                                    tier = SubscriptionTier.FREE
                                
                                # Create subscription
                                subscription = Subscription(
                                    tier=tier,
                                    stripe=stripe_details
                                )
                                
                                # Update the user
                                from ...models.user import UserUpdate
                                update_data = UserUpdate(subscription=subscription)
                                
                                await user_service.update_user(user_id, update_data)
                        except Exception:
                            pass  # Silent exception handling to avoid disrupting the flow

    elif event["type"] == "customer.subscription.created":
        # A new subscription was created
        subscription_data = event_object
        subscription_id = subscription_data.get('id')
        customer_id = subscription_data.get('customer')
        
        # Get the price ID
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")

        # Extract metadata from subscription if available
        metadata = subscription_data.get("metadata", {})
        
        # For guild subscriptions
        if is_guild_subscription:
            # Handle the case when we know it's a guild subscription but don't know which guild
            if not guild_id:
                # Try to find the guild by customer ID or subscription ID
                guild = None
                if customer_id:
                    guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_customer_id(customer_id)
                
                if not guild and subscription_id:
                    guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_subscription_id(subscription_id)
                    
                if guild:
                    guild_id = guild.guildId
                else:
                    # Extract guild_id from metadata if available
                    guild_id = metadata.get("guild_id")
            
            # Now process the subscription if we have a guild ID
            if guild_id:
                # Try to find the guild first - it might have been created in checkout
                guild = await guild_subscription_service.guild_repository.get_by_guild_id(guild_id)
                
                if guild:
                    # Get complete subscription details
                    stripe_details = GuildStripeService.convert_stripe_subscription_to_guild_format(subscription_data)
                    
                    from ...models.guild_subscription import GuildSubscriptionTier
                    # Apply the subscription details to the guild
                    if price_id:
                        tier = await GuildStripeService.get_tier_from_price_id(price_id)
                    else:
                        tier_str = metadata.get("tier", "free")
                        try:
                            tier = GuildSubscriptionTier(tier_str)
                        except ValueError:
                            tier = GuildSubscriptionTier.FREE
                    
                    # Update the guild with complete details
                    subscription = guild.subscription
                    
                    # Only update fields that are not already set
                    if not subscription.tier or subscription.tier == GuildSubscriptionTier.FREE:
                        subscription.tier = tier
                        
                    if hasattr(subscription, 'stripe') and subscription.stripe:
                        # Update stripe details but keep existing data where possible
                        if not subscription.stripe.stripe_subscription_id:
                            subscription.stripe.stripe_subscription_id = stripe_details.stripe_subscription_id
                            
                        if not subscription.stripe.stripe_price_id:
                            subscription.stripe.stripe_price_id = stripe_details.stripe_price_id
                            
                        # Always update these fields
                        subscription.stripe.status = stripe_details.status
                        subscription.stripe.current_period_start = stripe_details.current_period_start
                        subscription.stripe.current_period_end = stripe_details.current_period_end
                        subscription.stripe.interval = stripe_details.interval
                        subscription.stripe.interval_count = stripe_details.interval_count
                    else:
                        subscription.stripe = stripe_details
                        
                    # Update the guild
                    from ...models.guild import GuildUpdate
                    update_data = GuildUpdate(subscription=subscription)
                    
                    try:
                        await guild_subscription_service.guild_repository.update(str(guild.id), update_data)
                        
                        # Get updated guild
                        await guild_subscription_service.guild_repository.get_by_id(str(guild.id))
                    except Exception:
                        pass  # Silent exception handling to avoid disrupting the flow
                else:
                    # Handle full guild creation with subscription data
                    guild = await guild_subscription_service.handle_guild_subscription_created(subscription_data, guild_id)
        
        # For user subscriptions
        else:
            # Process the subscription
            await subscription_service.handle_subscription_created(subscription_data)
        
    elif event["type"] == "customer.subscription.updated":
        # A subscription was updated (e.g., plan change, payment method change)
        subscription_data = event_object
        subscription_id = subscription_data.get('id')
        customer_id = subscription_data.get('customer')
        
        # For guild subscriptions
        if is_guild_subscription:
            # Handle the case when we know it's a guild subscription but don't know which guild
            if not guild_id:
                # Try to find the guild by customer ID or subscription ID
                guild = None
                if customer_id:
                    guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_customer_id(customer_id)
                
                if not guild and subscription_id:
                    guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_subscription_id(subscription_id)
                    
                if guild:
                    guild_id = guild.guildId
            
            # Now process the subscription if we have a guild ID
            if guild_id:
                await guild_subscription_service.handle_guild_subscription_updated(subscription_data, guild_id)
        
        # For user subscriptions
        else:
            await subscription_service.handle_subscription_updated(subscription_data)
        
    elif event["type"] == "customer.subscription.deleted":
        # A subscription was deleted/cancelled
        subscription_data = event_object
        subscription_id = subscription_data.get('id')
        customer_id = subscription_data.get('customer')
        
        # For guild subscriptions
        if is_guild_subscription:
            # Handle the case when we know it's a guild subscription but don't know which guild
            if not guild_id:
                # Try to find the guild by customer ID or subscription ID
                guild = None
                if customer_id:
                    guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_customer_id(customer_id)
                
                if not guild and subscription_id:
                    guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_subscription_id(subscription_id)
                    
                if guild:
                    guild_id = guild.guildId
            
            # Now process the subscription if we have a guild ID
            if guild_id:
                await guild_subscription_service.handle_guild_subscription_deleted(subscription_data, guild_id)
        
        # For user subscriptions
        else:
            await subscription_service.handle_subscription_deleted(subscription_data)

    # Return a success response to acknowledge receipt of the event
    return {"status": "success", "event_type": event["type"]}