import json
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Body, Header, Query
from typing import Dict, Any, Optional

from app.api.routes.guild_subscriptions import get_guild_subscription_service
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
    return UserService(user_repository)


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


# @router.post("/webhook", status_code=status.HTTP_200_OK)
# async def handle_stripe_webhook(
#     request: Request,
#     stripe_signature: str = Header(None),
#     subscription_service: SubscriptionService = Depends(get_subscription_service),
#     user_service: UserService = Depends(get_user_service)  # Add user_service as a dependency
# ):
#     """
#     Handle Stripe webhook events
#     """
#     # Get the payload and validate signature
#     data = await request.body()
    
#     print(f"Webhook received with signature: {stripe_signature[:10]}...")
    
#     try:
#         event = stripe.Webhook.construct_event(
#             payload=data,
#             sig_header=stripe_signature,
#             secret=settings.STRIPE_WEBHOOK_SECRET
#         )
#         print(f"Webhook event constructed successfully. Event type: {event['type']}")
#     except ValueError as e:
#         # Invalid payload
#         print(f"Invalid payload error: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Invalid payload: {str(e)}"
#         )
#     except stripe.error.SignatureVerificationError as e:
#         # Invalid signature
#         print(f"Signature verification error: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Invalid signature: {str(e)}"
#         )
    
#     # Handle the event based on its type
#     if event["type"] == "checkout.session.completed":
#         # Payment was successful and the subscription was created
#         print("Checkout session completed event received")
#         session_data = event["data"]["object"]
#         session_id = session_data.get('id')
#         customer_id = session_data.get('customer')
#         subscription_id = session_data.get('subscription')
        
#         print(f"Session ID: {session_id}")
#         print(f"Customer ID: {customer_id}")
#         print(f"Subscription ID: {subscription_id}")
        
#         # Try to find and update the user
#         if customer_id:
#             # First, check if any user already has this customer ID
#             user_data = await subscription_service.subscription_repository.find_user_by_stripe_customer_id(customer_id)
            
#             if not user_data:
#                 # If not found by customer ID, try to get from metadata
#                 metadata = session_data.get('metadata', {})
#                 user_id = metadata.get('user_id')
                
#                 if user_id:
#                     print(f"Found user_id in metadata: {user_id}")
                    
#                     try:
#                         # Get user by ID
#                         user = await user_service.get_user(user_id)
                        
#                         # Update the user with Stripe customer and subscription IDs
#                         # Only if they don't already have them
#                         if (not user.subscription or 
#                             not user.subscription.stripe or 
#                             not user.subscription.stripe.stripe_customer_id):
                            
#                             # Create stripe subscription details
#                             from ...models.subscription import StripeSubscriptionDetails, EnhancedSubscription
                            
#                             stripe_details = StripeSubscriptionDetails(
#                                 stripe_customer_id=customer_id,
#                                 stripe_subscription_id=subscription_id
#                             )
                            
#                             # Get the tier from metadata or default to FREE
#                             tier_str = metadata.get('tier', 'free')
#                             from ...models.subscription import SubscriptionTier
                            
#                             try:
#                                 tier = SubscriptionTier(tier_str)
#                             except ValueError:
#                                 tier = SubscriptionTier.FREE
                            
#                             # Create enhanced subscription
#                             subscription = EnhancedSubscription(
#                                 tier=tier,
#                                 stripe=stripe_details
#                             )
                            
#                             # Update the user
#                             from ...models.user import UserUpdate
#                             update_data = UserUpdate(subscription=subscription)
                            
#                             print(f"Updating user {user_id} with Stripe customer and subscription IDs")
#                             updated_user = await user_service.update_user(user_id, update_data)
#                             print(f"User updated successfully with Stripe details")
#                     except HTTPException as e:
#                         print(f"Error fetching or updating user: {str(e)}")
#                     except Exception as e:
#                         print(f"Unexpected error updating user: {str(e)}")
        
#     elif event["type"] == "customer.subscription.created":
#         # A new subscription was created
#         print("Subscription created event received")
#         subscription_data = event["data"]["object"]
#         print(f"Subscription ID: {subscription_data.get('id')}")
#         print(f"Customer ID: {subscription_data.get('customer')}")
        
#         # Get the price ID
#         price_id = None
#         if subscription_data.get("items", {}).get("data"):
#             price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
#         print(f"Price ID: {price_id}")
        
#         # Process the subscription
#         user = await subscription_service.handle_subscription_created(subscription_data)
#         if user:
#             print(f"User updated successfully: {user.discordUsername} (ID: {user.id})")
#             print(f"New subscription tier: {user.subscription.tier}")
#         else:
#             print("Failed to update user: No matching user found")
        
#     elif event["type"] == "customer.subscription.updated":
#         # A subscription was updated (e.g., plan change, payment method change)
#         print("Subscription updated event received")
#         subscription_data = event["data"]["object"]
#         print(f"Subscription ID: {subscription_data.get('id')}")
#         print(f"Customer ID: {subscription_data.get('customer')}")
        
#         user = await subscription_service.handle_subscription_updated(subscription_data)
#         if user:
#             print(f"User updated successfully: {user.discordUsername} (ID: {user.id})")
#             print(f"Updated subscription tier: {user.subscription.tier}")
#         else:
#             print("Failed to update user: No matching user found")
        
#     elif event["type"] == "customer.subscription.deleted":
#         # A subscription was deleted/cancelled
#         print("Subscription deleted event received")
#         subscription_data = event["data"]["object"]
#         print(f"Subscription ID: {subscription_data.get('id')}")
#         print(f"Customer ID: {subscription_data.get('customer')}")
        
#         user = await subscription_service.handle_subscription_deleted(subscription_data)
#         if user:
#             print(f"User updated successfully: {user.discordUsername} (ID: {user.id})")
#             print(f"New subscription tier after deletion: {user.subscription.tier}")
#         else:
#             print("Failed to update user: No matching user found")
        
#     elif event["type"] == "invoice.payment_succeeded":
#         # Process successful invoice payment
#         print("Invoice payment succeeded event received")
#         invoice_data = event["data"]["object"]
#         print(f"Invoice ID: {invoice_data.get('id')}")
#         print(f"Customer ID: {invoice_data.get('customer')}")
#         print(f"Subscription ID: {invoice_data.get('subscription')}")
        
#     elif event["type"] == "invoice.payment_failed":
#         # Handle failed payment - this might trigger notifications or status changes
#         print("Invoice payment failed event received")
#         invoice_data = event["data"]["object"]
#         print(f"Invoice ID: {invoice_data.get('id')}")
#         print(f"Customer ID: {invoice_data.get('customer')}")
#         print(f"Subscription ID: {invoice_data.get('subscription')}")
    
#     # Return a success response to acknowledge receipt of the event
#     print(f"Webhook {event['type']} processed successfully")
#     return {"status": "success", "event_type": event["type"]}


# Updated portion of the webhook handler with better guild subscription detection

# First, improve the entity detection logic:
def is_guild_subscription_event(event_object):
    """Helper to determine if an event is for a guild subscription"""
    # Check metadata for entity_type=guild or guild_id
    metadata = event_object.get("metadata", {})
    if metadata and (metadata.get("entity_type") == "guild" or metadata.get("guild_id")):
        return True, metadata.get("guild_id")
    
    # If not found in metadata, check if customer ID is associated with a guild
    customer_id = event_object.get("customer")
    if customer_id:
        # TODO: Implement lookup in database
        pass
    
    return False, None

# Main webhook handler function:
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
    
    print(f"Webhook received with signature: {stripe_signature[:10]}...")
    
    try:
        event = stripe.Webhook.construct_event(
            payload=data,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
        print(f"Webhook event constructed successfully. Event type: {event['type']}")
    except ValueError as e:
        # Invalid payload
        print(f"Invalid payload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Signature verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}"
        )
    
    # Get the event data
    event_object = event["data"]["object"]
    
    # Determine if this is a guild or user subscription event
    is_guild_subscription = False
    guild_id = None
    
    # For checkout session events
    if event["type"] == "checkout.session.completed":
        is_guild_subscription, guild_id = is_guild_subscription_event(event_object)
        if is_guild_subscription:
            print(f"Detected guild subscription event for guild ID: {guild_id}")
    
    # For subscription events, check metadata directly
    elif event["type"].startswith("customer.subscription."):
        # First check metadata
        metadata = event_object.get("metadata", {})
        if metadata and (metadata.get("entity_type") == "guild" or metadata.get("guild_id")):
            is_guild_subscription = True
            guild_id = metadata.get("guild_id")
            print(f"Detected guild subscription event for guild ID: {guild_id}")
        
        # If not in metadata, check if this customer ID belongs to a guild
        elif not is_guild_subscription:
            customer_id = event_object.get("customer")
            if customer_id:
                # Try to find a guild with this customer ID
                guild = await guild_subscription_service.guild_repository.find_guild_by_stripe_customer_id(customer_id)
                if guild:
                    is_guild_subscription = True
                    guild_id = guild.guildId
                    print(f"Detected guild subscription event for customer ID: {customer_id}, guild ID: {guild_id}")
    
    # Handle the event based on its type
    if event["type"] == "checkout.session.completed":
        # Payment was successful and the subscription was created
        print("Checkout session completed event received")
        session_data = event_object
        session_id = session_data.get('id')
        customer_id = session_data.get('customer')
        subscription_id = session_data.get('subscription')
        
        print(f"Session ID: {session_id}")
        print(f"Customer ID: {customer_id}")
        print(f"Subscription ID: {subscription_id}")
        
        # Extract metadata
        metadata = session_data.get('metadata', {})
        
        # For guild subscriptions
        if is_guild_subscription and guild_id:
            print(f"Processing guild checkout completion for guild ID: {guild_id}")
            # Try to capture guild data from metadata
            tier_str = metadata.get('tier')
            tier = None
            if tier_str:
                try:
                    from ...models.guild_subscription import GuildSubscriptionTier
                    tier = GuildSubscriptionTier(tier_str)
                except ValueError:
                    pass
            
            print(f"Guild checkout completed, tier: {tier}, waiting for subscription event")
        
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
                        print(f"Found user_id in metadata: {user_id}")
                        
                        try:
                            # Get user by ID and update
                            user = await user_service.get_user(user_id)
                            
                            # Update user with subscription details
                            # ... (rest of user update code)
                        except Exception as e:
                            print(f"Error updating user: {str(e)}")
        
    elif event["type"] == "customer.subscription.created":
        # A new subscription was created
        print("Subscription created event received")
        subscription_data = event_object
        subscription_id = subscription_data.get('id')
        customer_id = subscription_data.get('customer')
        print(f"Subscription ID: {subscription_id}")
        print(f"Customer ID: {customer_id}")
        
        # Get the price ID
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
        print(f"Price ID: {price_id}")
        
        # For guild subscriptions
        if is_guild_subscription and guild_id:
            print(f"Processing guild subscription created for guild ID: {guild_id}")
            guild = await guild_subscription_service.handle_guild_subscription_created(subscription_data, guild_id)
            if guild:
                print(f"Guild updated successfully: {guild.guildName} (ID: {guild.id})")
                print(f"New subscription tier: {guild.subscription.tier}")
            else:
                print("Failed to update guild: No matching guild found")
        
        # For user subscriptions
        else:
            # Process the subscription
            user = await subscription_service.handle_subscription_created(subscription_data)
            if user:
                print(f"User updated successfully: {user.discordUsername} (ID: {user.id})")
                print(f"New subscription tier: {user.subscription.tier}")
            else:
                print("Failed to update user: No matching user found")
        
    elif event["type"] == "customer.subscription.updated":
        # A subscription was updated (e.g., plan change, payment method change)
        print("Subscription updated event received")
        subscription_data = event_object
        subscription_id = subscription_data.get('id')
        customer_id = subscription_data.get('customer')
        print(f"Subscription ID: {subscription_id}")
        print(f"Customer ID: {customer_id}")
        
        # For guild subscriptions
        if is_guild_subscription and guild_id:
            print(f"Processing guild subscription update for guild ID: {guild_id}")
            guild = await guild_subscription_service.handle_guild_subscription_updated(subscription_data, guild_id)
            if guild:
                print(f"Guild updated successfully: {guild.guildName} (ID: {guild.id})")
                print(f"Updated subscription tier: {guild.subscription.tier}")
            else:
                print("Failed to update guild: No matching guild found")
        
        # For user subscriptions
        else:
            user = await subscription_service.handle_subscription_updated(subscription_data)
            if user:
                print(f"User updated successfully: {user.discordUsername} (ID: {user.id})")
                print(f"Updated subscription tier: {user.subscription.tier}")
            else:
                print("Failed to update user: No matching user found")
        
    elif event["type"] == "customer.subscription.deleted":
        # A subscription was deleted/cancelled
        print("Subscription deleted event received")
        subscription_data = event_object
        subscription_id = subscription_data.get('id')
        customer_id = subscription_data.get('customer')
        print(f"Subscription ID: {subscription_id}")
        print(f"Customer ID: {customer_id}")
        
        # For guild subscriptions
        if is_guild_subscription and guild_id:
            print(f"Processing guild subscription deletion for guild ID: {guild_id}")
            guild = await guild_subscription_service.handle_guild_subscription_deleted(subscription_data, guild_id)
            if guild:
                print(f"Guild updated successfully: {guild.guildName} (ID: {guild.id})")
                print(f"New subscription tier after deletion: {guild.subscription.tier}")
            else:
                print("Failed to update guild: No matching guild found")
        
        # For user subscriptions
        else:
            user = await subscription_service.handle_subscription_deleted(subscription_data)
            if user:
                print(f"User updated successfully: {user.discordUsername} (ID: {user.id})")
                print(f"New subscription tier after deletion: {user.subscription.tier}")
            else:
                print("Failed to update user: No matching user found")
    
    # Return a success response to acknowledge receipt of the event
    print(f"Webhook {event['type']} processed successfully")
    return {"status": "success", "event_type": event["type"]}