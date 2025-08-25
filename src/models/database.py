"""Database models for the Slack emoji tracker."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """User model for storing Slack user information."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    slack_id = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    display_name = Column(String(255), nullable=True)
    real_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(slack_id='{self.slack_id}', email='{self.email}')>"


class EmojiUsage(Base):
    """Model for tracking emoji usage events."""

    __tablename__ = "emoji_usage"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who gave the emoji
    giver_slack_id = Column(String(20), nullable=False, index=True)
    
    # Who received the emoji (nullable for direct messages or own posts)
    receiver_slack_id = Column(String(20), nullable=True, index=True)
    
    # Emoji information
    emoji_name = Column(String(100), nullable=False, index=True)
    emoji_score = Column(Integer, nullable=False, default=1)
    
    # Slack context
    channel_id = Column(String(20), nullable=True, index=True)
    message_ts = Column(String(20), nullable=True, index=True)
    reaction_ts = Column(String(20), nullable=True)
    
    # Event type: 'reaction' or 'message'
    event_type = Column(String(20), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Additional context
    context = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation of the emoji usage."""
        return (
            f"<EmojiUsage(emoji='{self.emoji_name}', "
            f"giver='{self.giver_slack_id}', "
            f"receiver='{self.receiver_slack_id}', "
            f"score={self.emoji_score})>"
        )


class EmojiStats(Base):
    """Aggregated emoji statistics for faster queries."""

    __tablename__ = "emoji_stats"

    id = Column(Integer, primary_key=True, index=True)
    
    # User statistics
    user_slack_id = Column(String(20), nullable=False, index=True)
    
    # Score totals
    total_given_score = Column(Integer, default=0, nullable=False)
    total_received_score = Column(Integer, default=0, nullable=False)
    
    # Count totals
    total_given_count = Column(Integer, default=0, nullable=False)
    total_received_count = Column(Integer, default=0, nullable=False)
    
    # Emoji-specific stats (JSON or separate table could be used for more detail)
    most_given_emoji = Column(String(100), nullable=True)
    most_received_emoji = Column(String(100), nullable=True)
    
    # Timestamps
    last_activity = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of the emoji stats."""
        return (
            f"<EmojiStats(user='{self.user_slack_id}', "
            f"given={self.total_given_score}, "
            f"received={self.total_received_score})>"
        )


class Channel(Base):
    """Channel model for storing Slack channel information."""

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    slack_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    is_private = Column(String(10), nullable=True)  # 'true', 'false', or None
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of the channel."""
        return f"<Channel(slack_id='{self.slack_id}', name='{self.name}')>"