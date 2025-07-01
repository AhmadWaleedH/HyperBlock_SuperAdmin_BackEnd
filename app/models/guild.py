from enum import Enum
from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, field_serializer, field_validator
from datetime import datetime
from bson import ObjectId

from app.models.guild_subscription import GuildSubscription

from .user import PyObjectId, MongoBaseModel

# Role model for adminRoles
class AdminRole(BaseModel):
    roleId: str
    roleName: Optional[str] = None
    roleIconURL: Optional[str] = None

class ModRole(BaseModel):
    roleId: str
    roleName: Optional[str] = None
    roleIconURL: Optional[str] = None

# Base schemas
class BotChannels(BaseModel):
    hypeLogs: Optional[str] = None
    missionsHall: Optional[str] = None
    stadium: Optional[str] = None
    hyperMarket: Optional[str] = None
    raffles: Optional[str] = None

class UserChannels(BaseModel):
    events: Optional[str] = None
    myBag: Optional[str] = None
    raffles: Optional[str] = None
    shop: Optional[str] = None
    auctions: Optional[str] = None
    leaderboard: Optional[str] = None
    hyperNotes: Optional[str] = None

class ChatChannel(BaseModel):
    channelId: str
    channelName: str

class ReactionChannel(BaseModel):
    channelId: str
    channelName: str
    
class ChatConfig(BaseModel):
    chatChannels: List[ChatChannel] = Field(default_factory=list)
    cooldown: int = 0
    points: float = 0

class ReactionConfig(BaseModel):
    reactionChannels: List[ReactionChannel] = Field(default_factory=list)
    cooldown: int = 0
    points: float = 0

class GuildCounter(BaseModel):
    announcementCount: int = 0
    weeklyAnnouncementFrequency: int = 0
    eventCount: int = 0
    weeklyEventFrequency: int = 0
    totalActiveParticipants: int = 0
    storeUpdateCount: int = 0
    weeklyStoreUpdateFrequency: int = 0
    auctionUpdateCount: int = 0
    weeklyAuctionUpdateFrequency: int = 0
    socialTasksCount: int = 0
    weeklySocialTasksCounter: int = 0

class BotConfig(BaseModel):
    enabled: Optional[bool] = None
    prefix: Optional[str] = None
    adminRoles: List[AdminRole] = Field(default_factory=list)
    modRoles: List[ModRole] = Field(default_factory=list)
    channels: BotChannels = Field(default_factory=BotChannels)
    userChannels: UserChannels = Field(default_factory=UserChannels)
    chats: ChatConfig = Field(default_factory=ChatConfig)
    reactions: ReactionConfig = Field(default_factory=ReactionConfig)
    category: Optional[str] = None
    userCategory: Optional[str] = None

class PointsActions(BaseModel):
    like: Optional[float] = None
    retweet: Optional[float] = None
    comment: Optional[float] = None
    space: Optional[float] = None
    reaction: Optional[float] = None
    messagePoints: Optional[float] = None

class PointsSystem(BaseModel):
    name: Optional[str] = None
    exchangeRate: Optional[float] = None
    actions: PointsActions = Field(default_factory=PointsActions)

class AnalyticsMetrics(BaseModel):
    activeUsers: Optional[int] = None
    messageCount: Optional[int] = None
    taskCompletion: Optional[int] = None
    pointsUsage: Optional[int] = None

class GuildAnalytics(BaseModel):
    CAS: float = 0
    CHS: float = 0
    EAS: float = 0
    CCS: float = 0
    ERC: float = 0
    eventCost: float = 0
    vault: float = 0
    reservedPoints: float = 0
    metrics: AnalyticsMetrics = Field(default_factory=AnalyticsMetrics)

class CardConfig(BaseModel):
    cardImageBackground: Optional[str] = None
    communityIcon: Optional[str] = None
    hbIcon: Optional[str] = None
    tokenName: str = "HB"

# Main Guild model
class GuildModel(MongoBaseModel):
    guildId: str
    guildName: str
    botStatus: str = Field(..., description="Bot status: active, inactive, pending")
    guildIconURL: Optional[str] = None
    cardConfig: CardConfig = Field(default_factory=CardConfig)
    ownerId: Optional[PyObjectId] = None
    totalMembers: Optional[int] = None
    twitterUrl: Optional[str] = None
    # announcementChannelId: Optional[str] = None
    botConfig: BotConfig = Field(default_factory=BotConfig)
    pointsSystem: PointsSystem = Field(default_factory=PointsSystem)
    subscription: GuildSubscription = Field(default_factory=GuildSubscription)
    counter: GuildCounter = Field(default_factory=GuildCounter)
    analytics: GuildAnalytics = Field(default_factory=GuildAnalytics)
    shop: List[PyObjectId] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    
    # Serializer for ObjectId fields in lists
    @field_serializer('shop')
    def serialize_shop(self, shop_ids: List[ObjectId]) -> List[str]:
        return [str(shop_id) for shop_id in shop_ids]
    
    @field_validator('botStatus')
    def validate_bot_status(cls, value):
        if value not in ["active", "inactive", "pending"]:
            raise ValueError("Bot status must be one of: active, inactive, pending")
        return value
    
    @field_serializer('ownerId')
    def serialize_owner_id(self, owner_id: Optional[ObjectId]) -> Optional[str]:
        return str(owner_id) if owner_id else None

# Create/Update models
class GuildCreate(BaseModel):
    guildId: str
    guildName: str
    botStatus: str = "inactive"  # Default status is inactive
    guildIconURL: Optional[str] = None
    cardConfig: CardConfig = Field(default_factory=CardConfig)
    ownerId: Optional[PyObjectId] = None
    totalMembers: Optional[int] = None
    twitterUrl: Optional[str] = None
    # announcementChannelId: Optional[str] = None
    botConfig: Optional[BotConfig] = None
    pointsSystem: Optional[PointsSystem] = None
    subscription: Optional[GuildSubscription] = None
    counter: Optional[GuildCounter] = None

class GuildUpdate(BaseModel):
    guildName: Optional[str] = None
    botStatus: Optional[str] = None
    guildIconURL: Optional[str] = None
    cardConfig: CardConfig = Field(default_factory=CardConfig)
    ownerId: Optional[PyObjectId] = None
    totalMembers: Optional[int] = None
    twitterUrl: Optional[str] = None
    # announcementChannelId: Optional[str] = None
    botConfig: Optional[BotConfig] = None
    pointsSystem: Optional[PointsSystem] = None
    subscription: Optional[GuildSubscription] = None
    counter: Optional[GuildCounter] = None
    analytics: Optional[GuildAnalytics] = None

    @field_validator('botStatus')
    def validate_bot_status(cls, value):
        if value is not None and value not in ["active", "inactive", "pending"]:
            raise ValueError("Bot status must be one of: active, inactive, pending")
        return value

# Filter model
class GuildFilter(BaseModel):
    subscription_tier: Optional[str] = None
    bot_status: Optional[str] = None
    owner_discord_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    total_members_min: Optional[int] = None
    total_members_max: Optional[int] = None

# Response models
class GuildListResponse(BaseModel):
    total: int
    guilds: List[GuildModel]

class GuildUserPointsResponse(BaseModel):
    discordId: str
    discordUsername: str
    guildId: str
    points: int

class GuildTopUsersResponse(BaseModel):
    total: int
    users: List[GuildUserPointsResponse]

class GuildTeamMemberResponse(BaseModel):
    discordId: str
    discordUsername: str
    discordUserAvatarURL: Optional[str] = None
    guildId: str
    userType: str  # Will be "admin" or "owner"
    joinedAt: Optional[datetime] = None

class GuildTeamResponse(BaseModel):
    total: int
    team: List[GuildTeamMemberResponse]

# Points exchange models
class GuildPointsExchangeType(str, Enum):
    RESERVE_TO_VAULT = "reserve_to_vault"
    VAULT_TO_RESERVE = "vault_to_reserve"

class GuildPointsExchangeRequest(BaseModel):
    exchange_type: GuildPointsExchangeType
    points_amount: int = Field(gt=0, description="Amount of points to exchange (must be positive)")

class GuildPointsExchangeResponse(BaseModel):
    success: bool
    previous_reserve_points: int
    new_reserve_points: int
    previous_vault_points: int
    new_vault_points: int
    message: str

# Card Config Models
class CardConfigUpdateRequest(BaseModel):
    tokenName: Optional[str] = None

class CardConfigResponse(BaseModel):
    cardImageBackground: Optional[str] = None
    communityIcon: Optional[str] = None
    hbIcon: Optional[str] = None
    tokenName: str = ""

class CardUploadResponse(BaseModel):
    success: bool
    message: str
    component: str
    imageUrl: Optional[str] = None

class CardConfigResetResponse(BaseModel):
    success: bool
    message: str
    resetComponents: List[str]  # List of components that were reset
    
class CardConfigComponentResetResponse(BaseModel):
    success: bool
    message: str
    resetComponent: str