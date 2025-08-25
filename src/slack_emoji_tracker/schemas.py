"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """User information model."""
    slack_id: str
    display_name: Optional[str] = None
    real_name: Optional[str] = None
    email: Optional[str] = None


class EmojiStats(BaseModel):
    """Emoji statistics model."""
    emoji: str
    count: int
    score: int


class UserStats(BaseModel):
    """User statistics response model."""
    user: UserInfo
    totals: Dict[str, int]
    top_given: List[EmojiStats]
    top_received: List[EmojiStats]


class LeaderboardEntry(BaseModel):
    """Leaderboard entry model."""
    rank: int
    user: UserInfo
    stats: Dict[str, int]


class LeaderboardResponse(BaseModel):
    """Leaderboard response model."""
    entries: List[LeaderboardEntry]
    sort_by: str
    total_users: int


class HistoryEntry(BaseModel):
    """Emoji usage history entry."""
    emoji: str
    score: int
    type: str
    timestamp: str


class PaginationInfo(BaseModel):
    """Pagination information."""
    total: int
    limit: int
    offset: int
    has_more: bool


class UserHistoryResponse(BaseModel):
    """User history response model."""
    user: UserInfo
    history: List[HistoryEntry]
    pagination: PaginationInfo


class EmojiConfig(BaseModel):
    """Emoji configuration model."""
    score: int
    description: str


class EmojiConfigResponse(BaseModel):
    """Emoji configuration response model."""
    emojis: Dict[str, EmojiConfig]
    settings: Dict[str, Any]


class ChannelInfo(BaseModel):
    """Channel information model."""
    slack_id: str
    name: Optional[str] = None
    is_private: bool = False


class ChannelUserStats(BaseModel):
    """Channel user statistics model."""
    user: UserInfo
    count: int
    score: int


class ChannelStats(BaseModel):
    """Channel statistics response model."""
    channel: ChannelInfo
    totals: Dict[str, int]
    top_emojis: List[EmojiStats]
    top_users: List[ChannelUserStats]


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    database: bool
    slack: Optional[bool] = None
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None