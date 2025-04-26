from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from bson import ObjectId

from .user import PyObjectId, MongoBaseModel

# Participant and Winner models
class Participant(BaseModel):
    userId: str
    userName: Optional[str] = None

class Winner(BaseModel):
    userId: str
    userName: Optional[str] = None

# Main Raffle (Giveaway) model
class RaffleModel(MongoBaseModel):
    guildId: str
    guildName: Optional[str] = None
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    messageId: Optional[str] = None
    raffleTitle: str
    numWinners: int
    entryCost: int
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    chain: Optional[str] = None
    description: Optional[str] = None
    partnerTwitter: Optional[List[str]] = None
    winnerRole: Optional[str] = None
    winnerRoleName: Optional[str] = None
    roleRequired: Optional[str] = None
    roleRequiredName: Optional[str] = None
    entriesLimited: Optional[int] = None
    notes: Optional[str] = None
    totalParticipants: int = 0
    participants: List[Participant] = Field(default_factory=list)
    winners: List[Winner] = Field(default_factory=list)
    isExpired: bool = False
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

# Create/Update models
class RaffleCreate(BaseModel):
    guildId: str
    guildName: Optional[str] = None
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    messageId: Optional[str] = None
    raffleTitle: str
    numWinners: int
    entryCost: int
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    chain: Optional[str] = None
    description: Optional[str] = None
    partnerTwitter: Optional[List[str]] = None
    winnerRole: Optional[str] = None
    winnerRoleName: Optional[str] = None
    roleRequired: Optional[str] = None
    roleRequiredName: Optional[str] = None
    entriesLimited: Optional[int] = None
    notes: Optional[str] = None

class RaffleUpdate(BaseModel):
    channelId: Optional[str] = None
    channelName: Optional[str] = None
    messageId: Optional[str] = None
    raffleTitle: Optional[str] = None
    numWinners: Optional[int] = None
    entryCost: Optional[int] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    chain: Optional[str] = None
    description: Optional[str] = None
    partnerTwitter: Optional[List[str]] = None
    winnerRole: Optional[str] = None
    winnerRoleName: Optional[str] = None
    roleRequired: Optional[str] = None
    roleRequiredName: Optional[str] = None
    entriesLimited: Optional[int] = None
    notes: Optional[str] = None
    isExpired: Optional[bool] = None

# Participant operations
class AddParticipantModel(BaseModel):
    userId: str
    userName: Optional[str] = None

# Winner operations
class DrawWinnersModel(BaseModel):
    count: Optional[int] = None  # If not provided, use numWinners from raffle

# Filter model
class RaffleFilter(BaseModel):
    guildId: Optional[str] = None
    isExpired: Optional[bool] = None
    chain: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_winners: Optional[bool] = None
    entry_cost_min: Optional[int] = None
    entry_cost_max: Optional[int] = None

# Response models
class RaffleListResponse(BaseModel):
    total: int
    raffles: List[RaffleModel]

# Analytics models
class RaffleStatistics(BaseModel):
    raffle_id: str
    title: str
    total_participants: int
    entry_cost: int
    total_entry_value: int  # entry_cost * participants
    
class RaffleAnalytics(BaseModel):
    total_raffles: int
    active_raffles: int
    expired_raffles: int
    total_participants: int
    total_entry_points_spent: int
    raffles_by_guild: Dict[str, int]
    top_raffles: List[RaffleStatistics]
    raffles_by_chain: Dict[str, int]