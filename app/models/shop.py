from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_serializer, validator
from datetime import datetime
from bson import ObjectId

from .user import PyObjectId, MongoBaseModel

# Main ShopItem model
class ShopItemModel(MongoBaseModel):
    name: str
    price: float
    role: Optional[str] = None
    quantity: int = -1  # -1 means unlimited
    description: Optional[str] = None
    allowMultiplePurchases: bool = False
    blockchainId: Optional[str] = None
    requiredRoleToPurchase: Optional[str] = None
    server: Optional[PyObjectId] = None  # Reference to Guild
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    
    # Serializer for ObjectId field
    @field_serializer('server')
    def serialize_server(self, server: Optional[ObjectId]) -> Optional[str]:
        return str(server) if server else None
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

# Create/Update models
class ShopItemCreate(BaseModel):
    name: str
    price: float
    role: Optional[str] = None
    quantity: Optional[int] = -1
    description: Optional[str] = None
    allowMultiplePurchases: Optional[bool] = False
    blockchainId: Optional[str] = None
    requiredRoleToPurchase: Optional[str] = None
    server: Optional[str] = None  # Guild ID
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

class ShopItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    role: Optional[str] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    allowMultiplePurchases: Optional[bool] = None
    blockchainId: Optional[str] = None
    requiredRoleToPurchase: Optional[str] = None
    server: Optional[str] = None  # Guild ID
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        return v

# Purchase model
class PurchaseItemModel(BaseModel):
    userId: str
    quantity: int = 1
    
    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

# Filter model
class ShopItemFilter(BaseModel):
    server: Optional[str] = None  # Guild ID
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    has_quantity_available: Optional[bool] = None
    allow_multiple_purchases: Optional[bool] = None
    required_role: Optional[str] = None
    blockchain_id: Optional[str] = None

# Response models
class ShopItemListResponse(BaseModel):
    total: int
    shop_items: List[ShopItemModel]

# Analytics models
class ShopItemStatistics(BaseModel):
    item_id: str
    name: str
    price: float
    quantity_sold: int
    total_revenue: float
    
class ShopAnalytics(BaseModel):
    total_items: int
    available_items: int
    sold_out_items: int
    total_value: float
    items_by_server: Dict[str, int]
    top_items: List[ShopItemStatistics]
    price_distribution: Dict[str, int]  # Price ranges and count