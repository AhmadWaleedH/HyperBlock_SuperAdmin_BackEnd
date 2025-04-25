from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.guilds import GuildRepository
from ..models.guild import GuildModel, GuildCreate, GuildUpdate
from ..models.guild_subscription import (
    GuildSubscriptionTier, 
    GuildSubscription, 
    StripeGuildSubscriptionDetails
)
from ..models.user import UserModel
from .guild_stripe_service import GuildStripeService


class GuildSubscriptionService:
    def __init__(
        self, 
        guild_repository: GuildRepository
    ):
        self.guild_repository = guild_repository

    async def get_subscription_prices(self, tier: GuildSubscriptionTier) -> List[Dict[str, Any]]:
        """
        Get all available prices for a specific guild subscription tier
        """
        return await GuildStripeService.get_guild_subscription_prices(tier)

    async def create_guild_checkout_session(
        self, 
        user: UserModel, 
        guild_id: str,
        tier: GuildSubscriptionTier,
        price_id: Optional[str] = None,
        interval: Optional[str] = None,
        interval_count: Optional[int] = None,
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, str]:
        """
        Create a checkout session for a guild subscription
        """
        return await GuildStripeService.create_guild_checkout_session(
            user, 
            guild_id,
            tier, 
            price_id,
            interval,
            interval_count,
            success_url, 
            cancel_url,
            self.guild_repository
        )

    async def handle_guild_subscription_created(self, subscription_data: Dict[str, Any], guild_id: str) -> Optional[GuildModel]:
        """
        Handle a subscription.created webhook event for a guild
        """
        customer_id = subscription_data.get("customer")
        
        # Try to find guild by ID
        guild = await self.guild_repository.get_by_guild_id(guild_id)
        
        # Convert Stripe subscription to our format
        stripe_details = GuildStripeService.convert_stripe_subscription_to_guild_format(subscription_data)
        
        # Get the price ID to determine the subscription tier
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
        
        tier = await GuildStripeService.get_tier_from_price_id(price_id) if price_id else GuildSubscriptionTier.FREE
        
        # Calculate end date based on current period end
        current_period_end = stripe_details.current_period_end
        
        # Create subscription object
        enhanced_subscription = GuildSubscription(
            tier=tier,
            stripe=stripe_details
        )
        
        # If guild exists, update its subscription
        if guild:
            update_data = GuildUpdate(subscription=enhanced_subscription)
            await self.guild_repository.update(str(guild.id), update_data)
            return await self.guild_repository.get_by_id(str(guild.id))
        else:
            """
                TODO: Get guild details from Discord API
            """
            from ...models.guild import BotConfig, PointsSystem, GuildCounter
            
            new_guild = GuildCreate(
                guildId=guild_id,
                guildName=f"Guild {guild_id}",
                subscription=enhanced_subscription,
                botConfig=BotConfig(),
                pointsSystem=PointsSystem(),
                counter=GuildCounter()
            )
            
            created_guild = await self.guild_repository.create(new_guild)
            return created_guild
    
    async def handle_guild_subscription_updated(self, subscription_data: Dict[str, Any], guild_id: str) -> Optional[GuildModel]:
        """
        Handle a subscription.updated webhook event for a guild
        """        
        # Try to find guild by ID
        guild = await self.guild_repository.get_by_guild_id(guild_id)
        if not guild:
            return None
        
        # Convert Stripe subscription to our format
        stripe_details = GuildStripeService.convert_stripe_subscription_to_guild_format(subscription_data)
        
        # Get the price ID to determine the subscription tier
        price_id = None
        if subscription_data.get("items", {}).get("data"):
            price_id = subscription_data.get("items", {}).get("data")[0].get("price", {}).get("id")
        
        # Only update tier if price has changed
        current_price_id = guild.subscription.stripe.stripe_price_id if hasattr(guild.subscription, 'stripe') and guild.subscription.stripe else None
        
        if price_id and current_price_id != price_id:
            tier = await GuildStripeService.get_tier_from_price_id(price_id)
            
            # Create new subscription object with updated tier
            enhanced_subscription = GuildSubscription(
                tier=tier,
                stripe=stripe_details
            )
            
            # Update the guild
            update_data = GuildUpdate(subscription=enhanced_subscription)
            await self.guild_repository.update(str(guild.id), update_data)
        else:            
            # Use existing subscription data but update stripe details
            subscription = guild.subscription
            subscription.stripe = stripe_details
            
            
            # Update the guild
            update_data = GuildUpdate(subscription=subscription)
            await self.guild_repository.update(str(guild.id), update_data)
        
        # Return updated guild
        return await self.guild_repository.get_by_id(str(guild.id))
    
    async def handle_guild_subscription_deleted(self, subscription_data: Dict[str, Any], guild_id: str) -> Optional[GuildModel]:
        """
        Handle a subscription.deleted webhook event for a guild
        """        
        # Try to find guild by ID
        guild = await self.guild_repository.get_by_guild_id(guild_id)
        if not guild:
            return None
        
        # Convert Stripe subscription to our format
        stripe_details = GuildStripeService.convert_stripe_subscription_to_guild_format(subscription_data)
        
        # Downgrade to FREE tier
        enhanced_subscription = GuildSubscription(
            tier=GuildSubscriptionTier.FREE,
            stripe=stripe_details
        )
        
        # Update the guild
        update_data = GuildUpdate(subscription=enhanced_subscription)
        await self.guild_repository.update(str(guild.id), update_data)
        
        # Return updated guild
        return await self.guild_repository.get_by_id(str(guild.id))
    
    async def cancel_guild_subscription(
        self, 
        guild_id: str, 
        at_period_end: bool = True
    ) -> GuildModel:
        """
        Cancel a guild's subscription
        """        
        # Get the guild
        guild = await self.guild_repository.get_by_guild_id(guild_id)
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Call Stripe to cancel the subscription
        stripe_details = await GuildStripeService.cancel_guild_subscription(guild, at_period_end)
        
        # Update the guild's subscription details
        subscription = guild.subscription
        subscription.stripe = stripe_details
        
        # If immediate cancellation, update the tier to FREE
        if not at_period_end:
            subscription.tier = GuildSubscriptionTier.FREE
            subscription.autoRenew = False
            
        # Update the autoRenew flag regardless
        subscription.autoRenew = not at_period_end
        
        # Update the guild in the database
        update_data = GuildUpdate(subscription=subscription)
        await self.guild_repository.update(str(guild.id), update_data)
        
        # Return the updated guild
        return await self.guild_repository.get_by_id(str(guild.id))
    
    async def create_guild_portal_session(
        self, 
        guild_id: str, 
        return_url: str
    ) -> str:
        """
        Create a customer portal session for guild subscription management
        """
        # Get the guild
        guild = await self.guild_repository.get_by_guild_id(guild_id)
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild with ID {guild_id} not found"
            )
        
        # Create the portal session
        return await GuildStripeService.create_guild_portal_session(guild, return_url)