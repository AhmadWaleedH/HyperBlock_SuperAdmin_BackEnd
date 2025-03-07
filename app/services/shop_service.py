from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime

from ..db.repositories.shop import ShopRepository
from ..models.shop import (
    ShopItemModel, ShopItemCreate, ShopItemUpdate, ShopItemFilter, 
    ShopItemListResponse, PurchaseItemModel, ShopAnalytics
)
from ..models.user import PaginationParams

class ShopService:
    def __init__(self, shop_repository: ShopRepository):
        self.shop_repository = shop_repository

    async def create_shop_item(self, item_data: ShopItemCreate) -> ShopItemModel:
        """
        Create a new shop item
        """
        # Validate price is positive
        if item_data.price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be positive"
            )
        
        # Validate quantity (if not unlimited)
        if item_data.quantity != -1 and item_data.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be -1 (unlimited) or a non-negative value"
            )
        
        return await self.shop_repository.create(item_data)

    async def get_shop_item(self, item_id: str) -> ShopItemModel:
        """
        Get a shop item by ID
        """
        item = await self.shop_repository.get_by_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop item with ID {item_id} not found"
            )
        return item

    async def get_items_by_server(self, server_id: str, pagination: PaginationParams) -> ShopItemListResponse:
        """
        Get shop items by server ID
        """
        items, total = await self.shop_repository.get_items_by_server(server_id, pagination)
        return ShopItemListResponse(total=total, shop_items=items)

    async def update_shop_item(self, item_id: str, item_data: ShopItemUpdate) -> ShopItemModel:
        """
        Update a shop item
        """
        # Check if item exists
        existing_item = await self.shop_repository.get_by_id(item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop item with ID {item_id} not found"
            )
        
        # Validation for price if provided
        if item_data.price is not None and item_data.price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be positive"
            )
            
        # Validation for quantity if provided
        if item_data.quantity is not None and item_data.quantity != -1 and item_data.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be -1 (unlimited) or a non-negative value"
            )
        
        # Perform update
        updated_item = await self.shop_repository.update(item_id, item_data)
        return updated_item

    async def delete_shop_item(self, item_id: str) -> Dict[str, Any]:
        """
        Delete a shop item
        """
        # Check if item exists
        existing_item = await self.shop_repository.get_by_id(item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop item with ID {item_id} not found"
            )
        
        # Perform deletion
        success = await self.shop_repository.delete(item_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete shop item"
            )
        
        return {"message": f"Shop item with ID {item_id} deleted successfully"}

    async def purchase_item(self, item_id: str, purchase_data: PurchaseItemModel) -> ShopItemModel:
        """
        Process a purchase for a shop item
        """
        # Check if item exists
        existing_item = await self.shop_repository.get_by_id(item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop item with ID {item_id} not found"
            )
        
        # Check if item has quantity available
        if existing_item.quantity != -1 and existing_item.quantity < purchase_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient quantity available. Requested: {purchase_data.quantity}, Available: {existing_item.quantity}"
            )
        
        # Check if multiple purchases are allowed
        if not existing_item.allowMultiplePurchases and purchase_data.quantity > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This item does not allow multiple purchases"
            )
        
        # Process the purchase
        updated_item = await self.shop_repository.purchase_item(item_id, purchase_data)
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process purchase"
            )
        
        return updated_item

    async def get_shop_items(
        self, 
        filter_params: ShopItemFilter,
        pagination: PaginationParams
    ) -> ShopItemListResponse:
        """
        Get shop items with filters and pagination
        """
        items, total = await self.shop_repository.get_all_with_filters(filter_params, pagination)
        return ShopItemListResponse(total=total, shop_items=items)

    async def search_shop_items(
        self, 
        query: str,
        pagination: PaginationParams
    ) -> ShopItemListResponse:
        """
        Search shop items by a query string
        """
        items, total = await self.shop_repository.search(query, pagination)
        return ShopItemListResponse(total=total, shop_items=items)
    
    async def get_analytics(self) -> ShopAnalytics:
        """
        Get shop analytics
        """
        return await self.shop_repository.get_shop_analytics()