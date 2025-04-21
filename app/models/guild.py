from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from bson import ObjectId

from app.models.guild_subscription import GuildSubscription

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
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    cooldown: int = 0
    points: int = 0

class ReactionConfig(BaseModel):
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    cooldown: int = 0
    points: int = 0

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

class BotConfig(BaseModel):
    enabled: Optional[bool] = None
    prefix: Optional[str] = None
    adminRoles: List[Union[str, AdminRole]] = Field(default_factory=list)
    channels: BotChannels = Field(default_factory=BotChannels)
    userChannels: UserChannels = Field(default_factory=UserChannels)
    chats: ChatConfig = Field(default_factory=ChatConfig)
    reactions: ReactionConfig = Field(default_factory=ReactionConfig)
    category: Optional[str] = None
    userCategory: Optional[str] = None

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
    vault: int = 0
    reservedPoints: int = 0
    metrics: AnalyticsMetrics = Field(default_factory=AnalyticsMetrics)

# Main Guild model
class GuildModel(MongoBaseModel):
    guildId: str
    guildName: str
    guildIconURL: Optional[str] = None
    guildCardImageURL: Optional[str] = None
    ownerDiscordId: Optional[str] = None
    totalMembers: Optional[int] = None
    twitterUrl: Optional[str] = None
    announcementChannelId: Optional[str] = None
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

# Create/Update models
class GuildCreate(BaseModel):
    guildId: str
    guildName: str
    guildIconURL: Optional[str] = None
    guildCardImageURL: Optional[str] = None
    ownerDiscordId: Optional[str] = None
    totalMembers: Optional[int] = None
    twitterUrl: Optional[str] = None
    announcementChannelId: Optional[str] = None
    botConfig: Optional[BotConfig] = None
    pointsSystem: Optional[PointsSystem] = None
    subscription: Optional[GuildSubscription] = None
    counter: Optional[GuildCounter] = None

class GuildUpdate(BaseModel):
    guildName: Optional[str] = None
    guildIconURL: Optional[str] = None
    guildCardImageURL: Optional[str] = None
    ownerDiscordId: Optional[str] = None
    totalMembers: Optional[int] = None
    twitterUrl: Optional[str] = None
    announcementChannelId: Optional[str] = None
    botConfig: Optional[BotConfig] = None
    pointsSystem: Optional[PointsSystem] = None
    subscription: Optional[GuildSubscription] = None
    counter: Optional[GuildCounter] = None
    analytics: Optional[GuildAnalytics] = None

# Filter model
class GuildFilter(BaseModel):
    subscription_tier: Optional[str] = None
    bot_enabled: Optional[bool] = None
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