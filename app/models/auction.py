from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_serializer, validator
from datetime import datetime
from bson import ObjectId

from .user import PyObjectId, MongoBaseModel

# Bidder model
class Bidder(BaseModel):
    userId: str
    bidAmount: float
    walletAddress: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Winner model
class Winner(BaseModel):
    userId: Optional[str] = None
    winningBid: Optional[float] = None

# Main Auction model
class AuctionModel(MongoBaseModel):
    name: str
    quantity: int
    chain: str
    duration: datetime
    roleForWinner: Optional[str] = None
    guildId: str
    description: Optional[str] = None
    roleRequired: Optional[str] = None
    minimumBid: float = 0
    blindAuction: bool = False
    currentBid: float = 0
    currentBidder: Optional[str] = None
    bidders: List[Bidder] = Field(default_factory=list)
    status: Literal["active", "ended", "cancelled"] = "active"
    winner: Optional[Winner] = None
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

    @validator('minimumBid')
    def minimum_bid_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Minimum bid must be non-negative')
        return v

# Create/Update models
class AuctionCreate(BaseModel):
    name: str
    quantity: int
    chain: str
    duration: datetime
    roleForWinner: Optional[str] = None
    guildId: str
    description: Optional[str] = None
    roleRequired: Optional[str] = None
    minimumBid: float = 0
    blindAuction: bool = False

class AuctionUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    chain: Optional[str] = None
    duration: Optional[datetime] = None
    roleForWinner: Optional[str] = None
    description: Optional[str] = None
    roleRequired: Optional[str] = None
    minimumBid: Optional[float] = None
    blindAuction: Optional[bool] = None
    status: Optional[Literal["active", "ended", "cancelled"]] = None

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

    @validator('minimumBid')
    def minimum_bid_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Minimum bid must be non-negative')
        return v

# Bid model
class PlaceBidModel(BaseModel):
    userId: str
    bidAmount: float
    walletAddress: Optional[str] = None

# Filter model
class AuctionFilter(BaseModel):
    guildId: Optional[str] = None
    status: Optional[Literal["active", "ended", "cancelled"]] = None
    chain: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_bids: Optional[bool] = None
    min_bid: Optional[float] = None
    max_bid: Optional[float] = None
    bidder_id: Optional[str] = None

# Response models
class AuctionListResponse(BaseModel):
    total: int
    auctions: List[AuctionModel]

# Analytics models
class AuctionStatistics(BaseModel):
    auction_id: str
    name: str
    total_bids: int
    current_bid: float
    
class AuctionAnalytics(BaseModel):
    total_auctions: int
    active_auctions: int
    ended_auctions: int
    cancelled_auctions: int
    total_bids: int
    total_bid_value: float
    auctions_by_guild: Dict[str, int]
    top_auctions: List[AuctionStatistics]
    auctions_by_chain: Dict[str, int]
    avg_bids_per_auction: float