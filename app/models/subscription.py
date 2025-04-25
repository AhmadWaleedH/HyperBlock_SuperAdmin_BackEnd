from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class StripeSubscriptionDetails(BaseModel):
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    payment_method_id: Optional[str] = None


class SubscriptionPlan(BaseModel):
    id: str
    name: str
    description: str
    price_id: str
    amount: float
    currency: str = "usd"
    interval: str  # 'month' or 'year'
    features: List[str] = Field(default_factory=list)


class SubscriptionTier(str, Enum):
    FREE = "free"
    # SEED = "seed"  
    INDIVIDUAL = "individual"
    # FLARE = "flare"
    # TITAN = "titan"
    HYPERIUM = "hyperium"


# Subscription Model to work with Stripe
class Subscription(BaseModel):
    tier: SubscriptionTier = SubscriptionTier.FREE
    stripe: Optional[StripeSubscriptionDetails] = None


class SubscriptionCreate(BaseModel):
    tier: SubscriptionTier
    payment_method_id: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    tier: Optional[SubscriptionTier] = None
    payment_method_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


# Checkout Session Response
class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


# Subscription Response
class SubscriptionResponse(BaseModel):
    tier: SubscriptionTier
    status: Optional[SubscriptionStatus] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None