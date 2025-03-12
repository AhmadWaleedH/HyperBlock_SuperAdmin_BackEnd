from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field
from datetime import datetime

from .user import PyObjectId, MongoBaseModel

class SubscriptionTier(BaseModel):
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    features: List[str] = Field(default_factory=list)

class SubscriptionCreate(BaseModel):
    tier_id: PyObjectId
    billing_cycle: Literal["monthly", "yearly"]
    user_id: PyObjectId
    guild_id: Optional[PyObjectId] = None

class SubscriptionUpdate(BaseModel):
    tier_id: Optional[PyObjectId] = None
    billing_cycle: Optional[Literal["monthly", "yearly"]] = None
    auto_renew: Optional[bool] = None

class Subscription(MongoBaseModel):
    tier_id: PyObjectId
    user_id: PyObjectId
    guild_id: Optional[PyObjectId] = None
    billing_cycle: Literal["monthly", "yearly"]
    status: Literal["active", "cancelled", "expired", "pending"] = "pending"
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    auto_renew: bool = True
    payment_token: Optional[str] = None
    cybersource_customer_id: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)