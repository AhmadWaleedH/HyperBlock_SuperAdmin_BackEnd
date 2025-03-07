from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from bson import ObjectId

from .user import PyObjectId, MongoBaseModel

# Vote models
class UserVote(BaseModel):
    userId: str
    voteCount: int = 0

class MessageVote(BaseModel):
    messageId: str
    userVotes: List[UserVote] = Field(default_factory=list)

# Main Contest model
class ContestModel(MongoBaseModel):
    guildId: str
    title: str
    duration: datetime
    numberOfWinners: int
    description: str
    pointsForParticipants: int
    roleAssignedToParticipant: Optional[str] = None
    isActive: Optional[bool] = None
    channelId: Optional[str] = None
    pointsForWinners: Optional[List[int]] = None
    votes: List[MessageVote] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

# Create/Update models
class ContestCreate(BaseModel):
    guildId: str
    title: str
    duration: datetime
    numberOfWinners: int
    description: str
    pointsForParticipants: int
    roleAssignedToParticipant: Optional[str] = None
    isActive: Optional[bool] = None
    channelId: Optional[str] = None
    pointsForWinners: Optional[List[int]] = None

class ContestUpdate(BaseModel):
    title: Optional[str] = None
    duration: Optional[datetime] = None
    numberOfWinners: Optional[int] = None
    description: Optional[str] = None
    pointsForParticipants: Optional[int] = None
    roleAssignedToParticipant: Optional[str] = None
    isActive: Optional[bool] = None
    channelId: Optional[str] = None
    pointsForWinners: Optional[List[int]] = None

# Vote updates
class AddUserVoteModel(BaseModel):
    userId: str
    voteCount: int = 1

class MessageVoteUpdate(BaseModel):
    messageId: str
    userVote: AddUserVoteModel

# Filter model
class ContestFilter(BaseModel):
    guildId: Optional[str] = None
    isActive: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_participants: Optional[bool] = None

# Response models
class ContestListResponse(BaseModel):
    total: int
    contests: List[ContestModel]

# Analytics models
class ContestStatistics(BaseModel):
    contest_id: str
    title: str
    total_votes: int
    total_participants: int
    
class ContestAnalytics(BaseModel):
    total_contests: int
    active_contests: int
    total_votes_cast: int
    contests_by_guild: Dict[str, int]
    top_contests: List[ContestStatistics]