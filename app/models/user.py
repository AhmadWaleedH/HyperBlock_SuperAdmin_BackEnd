from typing import Dict, List, Optional, Annotated
from pydantic import BaseModel, Field, field_serializer, model_validator
from datetime import datetime
from bson import ObjectId
import json

# For Pydantic v2 - handling MongoDB ObjectId
class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]),
        ])

    @classmethod
    def validate(cls, value):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)

# Custom JSON encoder for ObjectId
class ObjectIdJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

# Base Model with ObjectId support for Pydantic v2
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    
    # Serializer for ObjectId fields
    @field_serializer('id')
    def serialize_object_id(self, id: Optional[ObjectId]) -> Optional[str]:
        return str(id) if id else None
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

# Subscription Schema
class Subscription(BaseModel):
    tier: str = "free"

# Social Media Links
class SocialLinks(BaseModel):
    x: Optional[str] = None
    tg: Optional[str] = None
    yt: Optional[str] = None
    tiktok: Optional[str] = None
    ig: Optional[str] = None

# Social Account Details
class TwitterAccount(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    profileUrl: Optional[str] = None

class SocialAccounts(BaseModel):
    twitter: Optional[TwitterAccount] = None

# Mint Wallets
class MintWallets(BaseModel):
    Ethereum: Optional[str] = None
    Solana: Optional[str] = None
    Bitcoin: Optional[str] = None
    Binance: Optional[str] = None
    Cardano: Optional[str] = None
    Polygon: Optional[str] = None
    Avalanche: Optional[str] = None
    Tron: Optional[str] = None
    Polkadot: Optional[str] = None
    Ripple: Optional[str] = None

# Server Membership Schema
class ServerMembership(BaseModel):
    guildId: str
    guildName: str
    guildIcon: Optional[str] = None
    subscription: Subscription = Field(default_factory=Subscription)
    status: str = "active"
    joinedAt: Optional[datetime] = None
    points: Optional[int] = None
    activeRaids: Optional[int] = None
    completedTasks: Optional[int] = None

# Purchase Schema
class Purchase(BaseModel):
    itemId: PyObjectId
    purchaseDate: datetime = Field(default_factory=datetime.now)
    totalPrice: float
    
    # Serializer for ObjectId fields in nested models
    @field_serializer('itemId')
    def serialize_object_id(self, itemId: ObjectId) -> str:
        return str(itemId)

# Bid Schema
class Bid(BaseModel):
    auctionId: PyObjectId
    bidAmount: float
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Serializer for ObjectId fields in nested models
    @field_serializer('auctionId')
    def serialize_object_id(self, auctionId: ObjectId) -> str:
        return str(auctionId)

# User Schema for DB
class UserModel(MongoBaseModel):
    discordId: str
    discordUsername: str
    discordUserAvatarURL: Optional[str] = None
    walletAddress: Optional[str] = None
    hyperBlockPoints: Optional[int] = None
    subscription: Subscription = Field(default_factory=Subscription)
    status: str = "active"
    socials: SocialLinks = Field(default_factory=SocialLinks)
    socialAccounts: Optional[SocialAccounts] = None
    mintWallets: Optional[MintWallets] = None
    serverMemberships: List[ServerMembership] = Field(default_factory=list)
    purchases: List[Purchase] = Field(default_factory=list)
    activeBids: List[Bid] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    lastActive: Optional[datetime] = None

# User Create Schema (for API input)
class UserCreate(BaseModel):
    discordId: str
    discordUsername: str
    discordUserAvatarURL: Optional[str] = None
    walletAddress: Optional[str] = None
    hyperBlockPoints: Optional[int] = 0
    subscription: Optional[Subscription] = None
    status: str = "active"
    socials: Optional[SocialLinks] = None

# User Update Schema (for API input)
class UserUpdate(BaseModel):
    discordUsername: Optional[str] = None
    discordUserAvatarURL: Optional[str] = None
    walletAddress: Optional[str] = None
    hyperBlockPoints: Optional[int] = None
    subscription: Optional[Subscription] = None
    status: Optional[str] = None
    socials: Optional[SocialLinks] = None
    mintWallets: Optional[MintWallets] = None
    lastActive: Optional[datetime] = None

# User Filter Schema (for query parameters)
class UserFilter(BaseModel):
    subscription_tier: Optional[str] = None
    status: Optional[str] = None
    wallet_type: Optional[str] = None
    min_points: Optional[int] = None
    max_points: Optional[int] = None
    discord_username: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

# Pagination
class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100

# User Response with pagination
class UserListResponse(BaseModel):
    total: int
    users: List[UserModel]