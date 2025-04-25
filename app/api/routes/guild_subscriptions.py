from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Body, Header, Query
from typing import Dict, Any, Optional, List

from ...models.user import UserModel
from ...models.guild_subscription import (
    GuildSubscriptionTier,
    GuildSubscriptionCreate,
    GuildSubscriptionResponse
)
from ...services.guild_subscription_service import GuildSubscriptionService
from ...services.user_service import UserService
from ...db.repositories.guilds import GuildRepository
from ...db.database import get_database
from ..dependencies import get_current_user


router = APIRouter()

async def get_guild_subscription_service(database = Depends(get_database)):
    guild_repository = GuildRepository(database)
    return GuildSubscriptionService(guild_repository)

async def get_user_service(database = Depends(get_database)):
    from ...db.repositories.users import UserRepository
    user_repository = UserRepository(database)
    guild_repository = GuildRepository(database)
    return UserService(user_repository, guild_repository)


@router.get("/prices/{tier}", response_model=List[Dict[str, Any]])
async def get_tier_prices(
    tier: GuildSubscriptionTier,
    guild_subscription_service: GuildSubscriptionService = Depends(get_guild_subscription_service),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get all available prices for a specific guild subscription tier
    """
    return await guild_subscription_service.get_subscription_prices(tier)


@router.post("/checkout", response_model=Dict[str, str])
async def create_guild_checkout_session(
    data: GuildSubscriptionCreate,
    success_url: str = Query(..., description="URL to redirect after successful payment"),
    cancel_url: str = Query(..., description="URL to redirect after cancelled payment"),
    current_user: UserModel = Depends(get_current_user),
    guild_subscription_service: GuildSubscriptionService = Depends(get_guild_subscription_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a Stripe checkout session for guild subscription purchase
    """
    # Get fresh user data to ensure we have the latest state
    current_user = await user_service.get_user(str(current_user.id))

    """
        TODO: Add permission check here (User should be admin of the guild)
            1. User should have permission to manage the guild
            2. User should have permission to manage subscriptions
    """
    
    return await guild_subscription_service.create_guild_checkout_session(
        current_user, 
        data.guild_id,
        data.tier, 
        data.price_id,
        data.interval,
        data.interval_count,
        success_url, 
        cancel_url
    )


@router.get("/{guild_id}", response_model=GuildSubscriptionResponse)
async def get_guild_subscription(
    guild_id: str,
    guild_subscription_service: GuildSubscriptionService = Depends(get_guild_subscription_service),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get subscription details for a guild
    """
    # Check if the guild exists
    guild = await guild_subscription_service.guild_repository.get_by_guild_id(guild_id)
    if not guild:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guild with ID {guild_id} not found"
        )
    
    if not guild.subscription:
        return GuildSubscriptionResponse(
            guild_id=guild_id,
            tier=GuildSubscriptionTier.FREE
        )
    
    # Handle case with newer GuildSubscription format
    if hasattr(guild.subscription, 'stripe'):
        stripe_details = guild.subscription.stripe
        return GuildSubscriptionResponse(
            guild_id=guild_id,
            tier=guild.subscription.tier,
            status=stripe_details.status if stripe_details else None,
            current_period_end=stripe_details.current_period_end if stripe_details else None,
            cancel_at_period_end=stripe_details.cancel_at_period_end if stripe_details else None,
            interval=stripe_details.interval if stripe_details else None,
            interval_count=stripe_details.interval_count if stripe_details else None,
            price_id=stripe_details.stripe_price_id if stripe_details else None
        )
    
    # Handle case with legacy GuildSubscription format
    return GuildSubscriptionResponse(
        guild_id=guild_id,
        tier=GuildSubscriptionTier(guild.subscription.tier)
    )


@router.post("/{guild_id}/cancel", response_model=GuildSubscriptionResponse)
async def cancel_guild_subscription(
    guild_id: str,
    at_period_end: bool = Body(True, embed=True),
    guild_subscription_service: GuildSubscriptionService = Depends(get_guild_subscription_service),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Cancel a guild's subscription
    """
    # Cancel the subscription
    guild = await guild_subscription_service.cancel_guild_subscription(guild_id, at_period_end)
    
    # Return the updated subscription information
    stripe_details = guild.subscription.stripe if hasattr(guild.subscription, 'stripe') else None
    
    return GuildSubscriptionResponse(
        guild_id=guild_id,
        tier=guild.subscription.tier,
        status=stripe_details.status if stripe_details else None,
        current_period_end=stripe_details.current_period_end if stripe_details else None,
        cancel_at_period_end=stripe_details.cancel_at_period_end if stripe_details else None,
        interval=stripe_details.interval if stripe_details else None,
        interval_count=stripe_details.interval_count if stripe_details else None,
        price_id=stripe_details.stripe_price_id if stripe_details else None
    )

@router.post("/{guild_id}/portal", response_model=Dict[str, str])
async def create_guild_portal_session(
    guild_id: str,
    return_url: str = Query(..., description="URL to return to after leaving the portal"),
    current_user: UserModel = Depends(get_current_user),
    guild_subscription_service: GuildSubscriptionService = Depends(get_guild_subscription_service)
):
    """
    Create a Stripe customer portal session for guild subscription management
    """
    portal_url = await guild_subscription_service.create_guild_portal_session(
        guild_id, 
        return_url
    )
    
    return {"portal_url": portal_url}