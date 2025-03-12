from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from datetime import datetime
import uuid

from ..db.repositories.payments import PaymentRepository
from ..db.repositories.subscriptions import SubscriptionRepository
from ..services.cybersource_service import CybersourceService
from ..models.payment import Payment, CheckoutSessionResponse

class PaymentService:
    def __init__(
        self, 
        payment_repository: PaymentRepository,
        subscription_repository: SubscriptionRepository,
        cybersource_service: CybersourceService
    ):
        self.payment_repository = payment_repository
        self.subscription_repository = subscription_repository
        self.cybersource_service = cybersource_service

    async def create_checkout_session(self, subscription_id: str, return_url: str) -> CheckoutSessionResponse:
        """Create a checkout session for a subscription"""
        # Get subscription
        subscription = await self.subscription_repository.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found"
            )
        
        # Get subscription tier
        tier = await self.subscription_repository.get_tier_by_id(str(subscription.tier_id))
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription tier not found"
            )
        
        # Determine price based on billing cycle
        price = tier.price_monthly if subscription.billing_cycle == "monthly" else tier.price_yearly
        
        # Generate reference ID
        reference_id = f"sub_{subscription_id}_{uuid.uuid4().hex[:8]}"
        print("reference_id", reference_id)
        # Create checkout session
        session = await self.cybersource_service.create_checkout_session(
            amount=price,
            currency="USD",
            reference_id=reference_id,
            subscription_type=subscription.billing_cycle,
            return_url=return_url
        )
        print(session)
        # Create payment record
        payment_data = {
            "user_id": subscription.user_id,
            "subscription_id": subscription.id,
            "amount": price,
            "currency": "USD",
            "status": "pending",
            "session_id": session["session_id"],
            "metadata": {
                "reference_id": reference_id,
                "billing_cycle": subscription.billing_cycle
            }
        }
        
        await self.payment_repository.create(payment_data)
        print("payment_data", payment_data)
        return CheckoutSessionResponse(
            session_id=session["session_id"],
            checkout_url=session["checkout_url"]
        )

    async def verify_payment(self, session_id: str) -> Dict[str, Any]:
        """Verify payment status from a checkout session"""
        # Get payment record
        payment = await self.payment_repository.get_by_session_id(session_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with session ID {session_id} not found"
            )
        
        # Verify session with Cybersource
        session_details = await self.cybersource_service.verify_checkout_session(session_id)
        
        # Update payment status based on session status
        status_mapping = {
            "COMPLETED": "completed",
            "AUTHORIZED": "completed",
            "FAILED": "failed",
            "CANCELLED": "failed"
        }
        
        payment_status = status_mapping.get(session_details["status"], "pending")
        
        # Update payment record
        await self.payment_repository.update_status(
            str(payment.id),
            payment_status,
            {
                "transaction_id": session_details.get("transaction_id"),
                "payment_token": session_details.get("payment_token"),
                "customer_id": session_details.get("customer_id"),
                "raw_response": session_details.get("raw_response")
            }
        )
        
        # If payment is completed, activate the subscription
        if payment_status == "completed":
            from ..services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(self.subscription_repository)
            
            await subscription_service.activate_subscription(
                str(payment.subscription_id),
                session_details.get("payment_token"),
                session_details.get("customer_id")
            )
        
        return {
            "status": payment_status,
            "session_status": session_details["status"]
        }

    async def process_webhook(self, payload: Dict[str, Any], signature: str, raw_payload: bytes) -> Dict[str, Any]:
        """Process Cybersource webhook notification"""
        # Verify webhook signature
        is_valid = await self.cybersource_service.verify_webhook_signature(signature, raw_payload)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
        
        # Extract session ID and event type
        event_type = payload.get("eventType")
        session_id = payload.get("id")
        
        if not session_id or not event_type:
            return {"status": "skipped", "reason": "Missing session ID or event type"}
        
        # Get payment record
        payment = await self.payment_repository.get_by_session_id(session_id)
        if not payment:
            return {"status": "skipped", "reason": "Payment not found"}
        
        # Update payment status based on event type
        if event_type == "payment.capture.completed":
            await self.payment_repository.update_status(
                str(payment.id),
                "completed",
                {"event_type": event_type, "webhook_payload": payload}
            )
            
            # Activate subscription
            from ..services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(self.subscription_repository)
            
            await subscription_service.activate_subscription(
                str(payment.subscription_id)
            )
            
            return {"status": "processed", "action": "subscription_activated"}
            
        elif event_type == "payment.authorization.failed":
            await self.payment_repository.update_status(
                str(payment.id),
                "failed",
                {"event_type": event_type, "webhook_payload": payload}
            )
            
            return {"status": "processed", "action": "payment_failed"}
        
        return {"status": "acknowledged", "action": "no_action_needed"}