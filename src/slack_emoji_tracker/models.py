"""Database models for the Slack Emoji Tracker."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User model for storing Slack user information."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    slack_id = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    real_name = Column(String(255), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    emoji_usage = relationship("EmojiUsage", back_populates="user", foreign_keys="EmojiUsage.user_id")
    stats = relationship("EmojiStats", back_populates="user")


class Channel(Base):
    """Channel model for storing Slack channel information."""

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    slack_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    is_private = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    emoji_usage = relationship("EmojiUsage", back_populates="channel")


class EmojiUsage(Base):
    """Model for tracking individual emoji usage events."""

    __tablename__ = "emoji_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    emoji_name = Column(String(100), nullable=False, index=True)
    emoji_score = Column(Integer, default=1)
    usage_type = Column(String(20), nullable=False)  # 'reaction' or 'message'
    message_ts = Column(String(50), nullable=True)  # Slack message timestamp
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For reactions
    created_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="emoji_usage", foreign_keys=[user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
    channel = relationship("Channel", back_populates="emoji_usage")


class EmojiStats(Base):
    """Model for storing aggregated emoji statistics."""

    __tablename__ = "emoji_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    emoji_name = Column(String(100), nullable=False)
    
    # Given stats (emojis this user has given)
    given_count = Column(Integer, default=0)
    given_score = Column(Integer, default=0)
    
    # Received stats (emojis this user has received)
    received_count = Column(Integer, default=0)
    received_score = Column(Integer, default=0)
    
    # Timestamps
    first_used = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="stats")

    __table_args__ = (
        # Unique constraint on user_id and emoji_name
        {"sqlite_autoincrement": True},
    )