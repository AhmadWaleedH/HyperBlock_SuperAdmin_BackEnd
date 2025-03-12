from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .user import PyObjectId, MongoBaseModel

class CheckoutSessionRequest(BaseModel):
    subscription_id: PyObjectId
    return_url: str

class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str

class PaymentWebhookPayload(BaseModel):
    session_id: str
    status: str
    event_type: str
    payload: Dict[str, Any]

class Payment(MongoBaseModel):
    user_id: PyObjectId
    subscription_id: PyObjectId
    amount: float
    currency: str = "USD"
    status: Literal["pending", "completed", "failed", "refunded"] = "pending"
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_token: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)