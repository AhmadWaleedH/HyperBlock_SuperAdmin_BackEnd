from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class GuildSubscriptionTier(str, Enum):
    FREE = "free"
    SEED = "seed"
    FLARE = "flare"
    TITAN = "titan"

class StripeGuildSubscriptionDetails(BaseModel):
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    status: str = "active"
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    payment_method_id: Optional[str] = None
    interval: Optional[str] = None
    interval_count: Optional[int] = None

# Guild Subscription Model
class GuildSubscription(BaseModel):
    tier: GuildSubscriptionTier = GuildSubscriptionTier.FREE
    stripe: Optional[StripeGuildSubscriptionDetails] = None

# Request models
class GuildSubscriptionCreate(BaseModel):
    guild_id: str
    tier: GuildSubscriptionTier
    price_id: Optional[str] = None  # specific price ID
    interval: Optional[str] = None  # e.g., "month", "year"
    interval_count: Optional[int] = None  # e.g., 1, 6, 12
    payment_method_id: Optional[str] = None

# Response models
class GuildSubscriptionResponse(BaseModel):
    guild_id: str
    tier: GuildSubscriptionTier
    status: Optional[str] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    interval: Optional[str] = None
    interval_count: Optional[int] = None
    auto_renew: Optional[bool] = None
    price_id: Optional[str] = None