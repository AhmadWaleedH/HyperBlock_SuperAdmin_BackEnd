from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import List, Optional

from ...models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionTier
from ...services.subscription_service import SubscriptionService
from ...db.repositories.subscriptions import SubscriptionRepository
from ...db.database import get_database
from ..dependencies import get_current_user, get_current_admin

router = APIRouter()

async def get_subscription_service(database = Depends(get_database)) -> SubscriptionService:
    subscription_repository = SubscriptionRepository(database)
    return SubscriptionService(subscription_repository)

@router.post("/", response_model=Subscription, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Create a new subscription (without payment processing)
    """
    print(subscription_data)
    return await subscription_service.create_subscription(subscription_data)

@router.get("/{subscription_id}", response_model=Subscription)
async def get_subscription(
    subscription_id: str = Path(..., title="The ID of the subscription to get"),
    current_user = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get a subscription by ID
    """
    return await subscription_service.get_subscription(subscription_id)

@router.get("/user/{user_id}", response_model=List[Subscription])
async def get_user_subscriptions(
    user_id: str = Path(..., title="The ID of the user"),
    current_user = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get all subscriptions for a user
    """
    return await subscription_service.get_user_subscriptions(user_id)

@router.get("/user/{user_id}/active", response_model=Optional[Subscription])
async def get_active_user_subscription(
    user_id: str = Path(..., title="The ID of the user"),
    current_user = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get active subscription for a user
    """
    return await subscription_service.get_active_user_subscription(user_id)

@router.patch("/{subscription_id}", response_model=Subscription)
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    subscription_id: str = Path(..., title="The ID of the subscription to update"),
    current_user = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Update a subscription
    """
    return await subscription_service.update_subscription(subscription_id, subscription_data)

@router.post("/{subscription_id}/cancel", response_model=Subscription)
async def cancel_subscription(
    subscription_id: str = Path(..., title="The ID of the subscription to cancel"),
    current_user = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Cancel a subscription
    """
    return await subscription_service.cancel_subscription(subscription_id)

@router.get("/tiers", response_model=List[SubscriptionTier])
async def get_subscription_tiers(
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get all available subscription tiers
    """
    return await subscription_service.get_subscription_tiers()