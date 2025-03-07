from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorCursor
from datetime import datetime
from bson import ObjectId

from ...models.shop import (
    ShopItemModel, ShopItemCreate, ShopItemUpdate, ShopItemFilter, 
    PurchaseItemModel, ShopAnalytics, ShopItemStatistics
)
from ...models.user import PaginationParams

class ShopRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.shopitems
        self.purchases_collection = database.purchases

    async def create(self, shop_item: ShopItemCreate) -> ShopItemModel:
        """
        Create a new shop item in the database
        """
        shop_item_data = shop_item.dict()
        shop_item_data["createdAt"] = datetime.now()
        shop_item_data["updatedAt"] = datetime.now()
        
        # Convert server string ID to ObjectId if provided
        if shop_item_data.get("server"):
            try:
                shop_item_data["server"] = ObjectId(shop_item_data["server"])
            except:
                # If conversion fails, set to None
                shop_item_data["server"] = None
        
        result = await self.collection.insert_one(shop_item_data)
        shop_item_data["_id"] = result.inserted_id
        
        return ShopItemModel(**shop_item_data)

    async def get_by_id(self, item_id: str) -> Optional[ShopItemModel]:
        """
        Get a shop item by MongoDB ID
        """
        if not ObjectId.is_valid(item_id):
            return None
            
        shop_item = await self.collection.find_one({"_id": ObjectId(item_id)})
        if shop_item:
            return ShopItemModel(**shop_item)
        return None

    async def get_items_by_server(self, server_id: str, pagination: PaginationParams) -> Tuple[List[ShopItemModel], int]:
        """
        Get shop items by server ID
        """
        # Try to convert to ObjectId, if it's a valid MongoDB ID
        server_query = {"server": None}
        if ObjectId.is_valid(server_id):
            server_query = {"server": ObjectId(server_id)}
        
        # Count total matches
        total = await self.collection.count_documents(server_query)
        
        # Get paginated results
        cursor = self.collection.find(server_query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        shop_items = []
        async for item_doc in cursor:
            shop_items.append(ShopItemModel(**item_doc))
        
        return shop_items, total

    async def update(self, item_id: str, item_update: ShopItemUpdate) -> Optional[ShopItemModel]:
        """
        Update a shop item
        """
        if not ObjectId.is_valid(item_id):
            return None
            
        update_data = item_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            # Convert server string ID to ObjectId if provided
            if update_data.get("server"):
                try:
                    update_data["server"] = ObjectId(update_data["server"])
                except:
                    # If conversion fails, set to None
                    update_data["server"] = None
            
            await self.collection.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(item_id)

    async def delete(self, item_id: str) -> bool:
        """
        Delete a shop item
        """
        if not ObjectId.is_valid(item_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(item_id)})
        return result.deleted_count > 0

    async def purchase_item(self, item_id: str, purchase: PurchaseItemModel) -> Optional[ShopItemModel]:
        """
        Process an item purchase and update inventory
        """
        if not ObjectId.is_valid(item_id):
            return None
        
        # Get the shop item
        shop_item = await self.get_by_id(item_id)
        if not shop_item:
            return None
        
        # Check if item has quantity available
        if shop_item.quantity != -1 and shop_item.quantity < purchase.quantity:
            return None
        
        # Update inventory if item has limited quantity
        if shop_item.quantity != -1:
            await self.collection.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$inc": {"quantity": -purchase.quantity},
                    "$set": {"updatedAt": datetime.now()}
                }
            )
        
        # Record the purchase in purchases collection
        purchase_record = {
            "itemId": ObjectId(item_id),
            "userId": purchase.userId,
            "quantity": purchase.quantity,
            "purchaseDate": datetime.now(),
            "totalPrice": shop_item.price * purchase.quantity
        }
        
        await self.purchases_collection.insert_one(purchase_record)
        
        # Return updated shop item
        return await self.get_by_id(item_id)

    async def get_all_with_filters(
        self, 
        filter_params: ShopItemFilter,
        pagination: PaginationParams
    ) -> Tuple[List[ShopItemModel], int]:
        """
        Get all shop items with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.server:
            if ObjectId.is_valid(filter_params.server):
                query["server"] = ObjectId(filter_params.server)
            else:
                query["server"] = None
            
        if filter_params.min_price is not None:
            query["price"] = query.get("price", {})
            query["price"]["$gte"] = filter_params.min_price
            
        if filter_params.max_price is not None:
            query["price"] = query.get("price", {})
            query["price"]["$lte"] = filter_params.max_price
            
        if filter_params.has_quantity_available is not None:
            if filter_params.has_quantity_available:
                query["$or"] = [
                    {"quantity": -1},  # Unlimited
                    {"quantity": {"$gt": 0}}  # Has stock
                ]
            else:
                query["quantity"] = 0  # Out of stock
        
        if filter_params.allow_multiple_purchases is not None:
            query["allowMultiplePurchases"] = filter_params.allow_multiple_purchases
            
        if filter_params.required_role:
            query["requiredRoleToPurchase"] = filter_params.required_role
            
        if filter_params.blockchain_id:
            query["blockchainId"] = filter_params.blockchain_id
        
        # Count total documents matching the query
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        shop_items = []
        async for item_doc in cursor:
            shop_items.append(ShopItemModel(**item_doc))
        
        return shop_items, total

    async def search(self, query_string: str, pagination: PaginationParams) -> Tuple[List[ShopItemModel], int]:
        """
        Search shop items by a general query string
        """
        # Building a search query across multiple fields
        query = {
            "$or": [
                {"name": {"$regex": query_string, "$options": "i"}},
                {"description": {"$regex": query_string, "$options": "i"}},
                {"blockchainId": {"$regex": query_string, "$options": "i"}},
            ]
        }
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        shop_items = []
        async for item_doc in cursor:
            shop_items.append(ShopItemModel(**item_doc))
        
        return shop_items, total
    
    async def get_shop_analytics(self) -> ShopAnalytics:
        """
        Get analytics for all shop items
        """
        # Count total items
        total_items = await self.collection.count_documents({})
        
        # Count available and sold out items
        available_items = await self.collection.count_documents({
            "$or": [
                {"quantity": -1},  # Unlimited
                {"quantity": {"$gt": 0}}  # Has stock
            ]
        })
        sold_out_items = await self.collection.count_documents({"quantity": 0})
        
        # Calculate total value of all items
        value_pipeline = [
            {"$group": {"_id": None, "totalValue": {"$sum": "$price"}}}
        ]
        value_result = await self.collection.aggregate(value_pipeline).to_list(length=None)
        total_value = value_result[0]["totalValue"] if value_result else 0
        
        # Group items by server
        server_pipeline = [
            {"$group": {"_id": "$server", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        server_results = await self.collection.aggregate(server_pipeline).to_list(length=None)
        
        # Convert ObjectId to string for server IDs
        items_by_server = {}
        for item in server_results:
            server_id = str(item["_id"]) if item["_id"] else "None"
            items_by_server[server_id] = item["count"]
        
        # Get top items by purchase count from purchases collection
        top_items_pipeline = [
            {"$group": {
                "_id": "$itemId", 
                "totalQuantity": {"$sum": "$quantity"},
                "totalRevenue": {"$sum": "$totalPrice"}
            }},
            {"$sort": {"totalQuantity": -1}},
            {"$limit": 5}
        ]
        top_items_result = await self.purchases_collection.aggregate(top_items_pipeline).to_list(length=None)
        
        # Fetch item details for top items
        top_items = []
        for item in top_items_result:
            item_details = await self.collection.find_one({"_id": item["_id"]})
            if item_details:
                top_items.append(ShopItemStatistics(
                    item_id=str(item["_id"]),
                    name=item_details["name"],
                    price=item_details["price"],
                    quantity_sold=item["totalQuantity"],
                    total_revenue=item["totalRevenue"]
                ))
        
        # Calculate price distribution
        price_ranges = {
            "0-50": 0,
            "51-100": 0,
            "101-500": 0,
            "501-1000": 0,
            "1001+": 0
        }
        
        async for item in self.collection.find({}):
            price = item["price"]
            if price <= 50:
                price_ranges["0-50"] += 1
            elif price <= 100:
                price_ranges["51-100"] += 1
            elif price <= 500:
                price_ranges["101-500"] += 1
            elif price <= 1000:
                price_ranges["501-1000"] += 1
            else:
                price_ranges["1001+"] += 1
        
        return ShopAnalytics(
            total_items=total_items,
            available_items=available_items,
            sold_out_items=sold_out_items,
            total_value=total_value,
            items_by_server=items_by_server,
            top_items=top_items,
            price_distribution=price_ranges
        )