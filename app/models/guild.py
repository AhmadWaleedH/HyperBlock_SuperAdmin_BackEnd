from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from bson import ObjectId

from .user import PyObjectId, MongoBaseModel

# Role model for adminRoles
class AdminRole(BaseModel):
    roleId: str
    roleIconURL: Optional[str] = None

# Base schemas
class BotChannels(BaseModel):
    hypeLogs: Optional[str] = None
    missionsHall: Optional[str] = None
    stadium: Optional[str] = None
    hyperMarket: Optional[str] = None
    hyperNotes: Optional[str] = None
    raffles: Optional[str] = None

class UserChannels(BaseModel):
    events: Optional[str] = None
    myBag: Optional[str] = None
    raffles: Optional[str] = None
    shop: Optional[str] = None
    auctions: Optional[str] = None

class ChatConfig(BaseModel):
    channels: List[str] = Field(default_factory=list)
    cooldown: int = 0
    points: int = 0

class ReactionConfig(BaseModel):
    channels: List[str] = Field(default_factory=list)
    cooldown: int = 0
    points: int = 0

class BotConfig(BaseModel):
    enabled: Optional[bool] = None
    prefix: Optional[str] = None
    adminRoles: List[Union[str, AdminRole]] = Field(default_factory=list)
    channels: BotChannels = Field(default_factory=BotChannels)
    userChannels: UserChannels = Field(default_factory=UserChannels)
    chats: ChatConfig = Field(default_factory=ChatConfig)
    reactions: ReactionConfig = Field(default_factory=ReactionConfig)

class PointsActions(BaseModel):
    like: Optional[int] = None
    retweet: Optional[int] = None
    comment: Optional[int] = None
    space: Optional[int] = None
    reaction: Optional[int] = None
    messagePoints: Optional[int] = None

class PointsSystem(BaseModel):
    name: Optional[str] = None
    exchangeRate: Optional[float] = None
    actions: PointsActions = Field(default_factory=PointsActions)

class GuildSubscription(BaseModel):
    tier: Optional[str] = "Free"
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    autoRenew: Optional[bool] = None

class AnalyticsMetrics(BaseModel):
    activeUsers: Optional[int] = None
    messageCount: Optional[int] = None
    taskCompletion: Optional[int] = None
    pointsUsage: Optional[int] = None
    chatHealth: Optional[int] = None

class GuildAnalytics(BaseModel):
    rating: Optional[str] = None
    rank: Optional[int] = None
    isTop10: Optional[bool] = None
    metrics: AnalyticsMetrics = Field(default_factory=AnalyticsMetrics)

# Main Guild model
class GuildModel(MongoBaseModel):
    guildId: str
    guildName: str
    guildIconURL: Optional[str] = None
    ownerDiscordId: str
    twitterUrl: Optional[str] = None
    category: Optional[str] = None
    userCategory: Optional[str] = None
    announcementChannelId: Optional[str] = None
    botConfig: BotConfig = Field(default_factory=BotConfig)
    pointsSystem: PointsSystem = Field(default_factory=PointsSystem)
    subscription: GuildSubscription = Field(default_factory=GuildSubscription)
    analytics: GuildAnalytics = Field(default_factory=GuildAnalytics)
    shop: List[PyObjectId] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    
    # Serializer for ObjectId fields in lists
    @field_serializer('shop')
    def serialize_shop(self, shop_ids: List[ObjectId]) -> List[str]:
        return [str(shop_id) for shop_id in shop_ids]

# Create/Update models
class GuildCreate(BaseModel):
    guildId: str
    guildName: str
    guildIconURL: Optional[str] = None
    ownerDiscordId: str
    twitterUrl: Optional[str] = None
    category: Optional[str] = None
    userCategory: Optional[str] = None
    announcementChannelId: Optional[str] = None
    botConfig: Optional[BotConfig] = None
    pointsSystem: Optional[PointsSystem] = None
    subscription: Optional[GuildSubscription] = None

class GuildUpdate(BaseModel):
    guildName: Optional[str] = None
    guildIconURL: Optional[str] = None
    ownerDiscordId: Optional[str] = None
    twitterUrl: Optional[str] = None
    category: Optional[str] = None
    userCategory: Optional[str] = None
    announcementChannelId: Optional[str] = None
    botConfig: Optional[BotConfig] = None
    pointsSystem: Optional[PointsSystem] = None
    subscription: Optional[GuildSubscription] = None
    analytics: Optional[GuildAnalytics] = None

# Filter model
class GuildFilter(BaseModel):
    subscription_tier: Optional[str] = None
    category: Optional[str] = None
    user_category: Optional[str] = None
    rating: Optional[str] = None
    is_top10: Optional[bool] = None
    bot_enabled: Optional[bool] = None
    owner_discord_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

# Response models
class GuildListResponse(BaseModel):
    total: int
    guilds: List[GuildModel]