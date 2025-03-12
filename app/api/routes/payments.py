from fastapi import APIRouter, Depends, Path, HTTPException, status, Request, Header
from typing import Optional, Dict, Any

from ...models.payment import CheckoutSessionRequest, CheckoutSessionResponse
from ...services.payment_service import PaymentService
from ...services.cybersource_service import CybersourceService
from ...db.repositories.payments import PaymentRepository
from ...db.repositories.subscriptions import SubscriptionRepository
from ...db.database import get_database
from ..dependencies import get_current_user

router = APIRouter()

async def get_payment_service(database = Depends(get_database)) -> PaymentService:
    payment_repository = PaymentRepository(database)
    subscription_repository = SubscriptionRepository(database)
    cybersource_service = CybersourceService()
    return PaymentService(payment_repository, subscription_repository, cybersource_service)

async def get_cybersource_service() -> CybersourceService:
    return CybersourceService()

@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request_data: CheckoutSessionRequest,
    current_user = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Create a checkout session for a subscription
    """
    return await payment_service.create_checkout_session(
        str(request_data.subscription_id),
        request_data.return_url
    )

@router.get("/verify/{session_id}")
async def verify_payment(
    session_id: str = Path(..., title="The Cybersource session ID"),
    current_user = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Verify payment status after checkout completion
    """
    return await payment_service.verify_payment(session_id)

@router.post("/webhooks/cybersource")
async def cybersource_webhook(
    request: Request,
    signature: Optional[str] = Header(None),
    payment_service: PaymentService = Depends(get_payment_service)
):
    """
    Handle Cybersource webhook notifications
    """
    # Get the raw payload
    payload_bytes = await request.body()
    payload = await request.json()
    
    # Process webhook
    return await payment_service.process_webhook(payload, signature, payload_bytes)