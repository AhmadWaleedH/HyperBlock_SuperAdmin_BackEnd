from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .user import PyObjectId, MongoBaseModel

# Main EmbedMessage model
class EmbedMessageModel(MongoBaseModel):
    itemId: str
    guildId: str
    channelId: str
    messageId: str
    itemName: Optional[str] = None
    guildName: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

# Create/Update models
class EmbedMessageCreate(BaseModel):
    itemId: str
    guildId: str
    channelId: str
    messageId: str

class EmbedMessageUpdate(BaseModel):
    itemId: Optional[str] = None
    channelId: Optional[str] = None
    messageId: Optional[str] = None

# Filter model
class EmbedMessageFilter(BaseModel):
    guildId: Optional[str] = None
    channelId: Optional[str] = None
    itemId: Optional[str] = None

# Response models
class EmbedMessageListResponse(BaseModel):
    total: int
    embed_messages: List[EmbedMessageModel]

# Analytics models
class EmbedMessageAnalytics(BaseModel):
    total_embeds: int
    embeds_by_guild: Dict[str, int]
    embeds_by_channel: Dict[str, int]