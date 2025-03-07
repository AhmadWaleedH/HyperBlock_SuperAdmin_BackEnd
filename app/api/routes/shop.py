from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models.shop import (
    ShopItemModel, ShopItemCreate, ShopItemUpdate, ShopItemFilter, 
    ShopItemListResponse, PurchaseItemModel, ShopAnalytics
)
from ...models.user import PaginationParams
from ...services.shop_service import ShopService
from ...db.repositories.shop import ShopRepository
from ...db.database import get_database
from ..dependencies import get_current_admin

router = APIRouter()

async def get_shop_service(database = Depends(get_database)) -> ShopService:
    shop_repository = ShopRepository(database)
    return ShopService(shop_repository)

@router.post("/items/", response_model=ShopItemModel, status_code=status.HTTP_201_CREATED)
async def create_shop_item(
    item_data: ShopItemCreate,
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Create a new shop item
    """
    return await shop_service.create_shop_item(item_data)

@router.get("/items/{item_id}", response_model=ShopItemModel)
async def get_shop_item(
    item_id: str = Path(..., title="The ID of the shop item to get"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Get a shop item by ID
    """
    return await shop_service.get_shop_item(item_id)

@router.get("/server/{server_id}", response_model=ShopItemListResponse)
async def get_items_by_server(
    server_id: str = Path(..., title="The server ID to get shop items for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Get shop items by server ID
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await shop_service.get_items_by_server(server_id, pagination)

@router.patch("/items/{item_id}", response_model=ShopItemModel)
async def update_shop_item(
    item_data: ShopItemUpdate,
    item_id: str = Path(..., title="The ID of the shop item to update"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Update a shop item
    """
    return await shop_service.update_shop_item(item_id, item_data)

@router.delete("/items/{item_id}")
async def delete_shop_item(
    item_id: str = Path(..., title="The ID of the shop item to delete"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Delete a shop item
    """
    return await shop_service.delete_shop_item(item_id)

@router.post("/items/{item_id}/purchase", response_model=ShopItemModel)
async def purchase_item(
    purchase_data: PurchaseItemModel,
    item_id: str = Path(..., title="The ID of the shop item to purchase"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Purchase a shop item
    """
    return await shop_service.purchase_item(item_id, purchase_data)

@router.get("/items/", response_model=ShopItemListResponse)
async def list_shop_items(
    server: Optional[str] = Query(None, description="Filter by server ID"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    has_quantity_available: Optional[bool] = Query(None, description="Filter items with available quantity"),
    allow_multiple_purchases: Optional[bool] = Query(None, description="Filter items allowing multiple purchases"),
    required_role: Optional[str] = Query(None, description="Filter by required role to purchase"),
    blockchain_id: Optional[str] = Query(None, description="Filter by blockchain ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    List shop items with filtering and pagination
    """
    # Create filter and pagination objects
    filter_params = ShopItemFilter(
        server=server,
        min_price=min_price,
        max_price=max_price,
        has_quantity_available=has_quantity_available,
        allow_multiple_purchases=allow_multiple_purchases,
        required_role=required_role,
        blockchain_id=blockchain_id
    )
    pagination = PaginationParams(skip=skip, limit=limit)
    
    return await shop_service.get_shop_items(filter_params, pagination)

@router.get("/search/", response_model=ShopItemListResponse)
async def search_shop_items(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Search shop items by a query string
    """
    pagination = PaginationParams(skip=skip, limit=limit)
    return await shop_service.search_shop_items(query, pagination)

@router.get("/analytics/summary", response_model=ShopAnalytics)
async def get_shop_analytics(
    shop_service: ShopService = Depends(get_shop_service)
):
    """
    Get analytics summary for the shop
    """
    return await shop_service.get_analytics()