"""Core service for emoji tracking and statistics."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session
from slack_sdk.web import WebClient

from .config import config
from .models import Channel, EmojiStats, EmojiUsage, User

logger = logging.getLogger(__name__)


class EmojiService:
    """Service for managing emoji tracking and statistics."""

    def __init__(self, db_session: Session, web_client: Optional[WebClient] = None):
        """Initialize the service with a database session and optional Slack web client."""
        self.db = db_session
        self.web_client = web_client

    def create_or_update_user(
        self,
        slack_id: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        real_name: Optional[str] = None,
        is_bot: bool = False,
        fetch_from_slack: bool = True,
    ) -> User:
        """Create a new user or update existing user information."""
        user = self.db.query(User).filter(User.slack_id == slack_id).first()
        
        # Fetch user information from Slack API if available and requested
        slack_user_info = None
        if fetch_from_slack and self.web_client:
            try:
                response = self.web_client.users_info(user=slack_id)
                if response.get("ok"):
                    slack_user_info = response.get("user", {})
                    profile = slack_user_info.get("profile", {})
                    
                    # Override with Slack data if not explicitly provided
                    if email is None:
                        email = profile.get("email")
                    if display_name is None:
                        display_name = profile.get("display_name") or slack_user_info.get("name")
                    if real_name is None:
                        real_name = profile.get("real_name")
                    is_bot = slack_user_info.get("is_bot", False)
                    
                    logger.info(f"Fetched user info from Slack for {slack_id}: {display_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch user info from Slack for {slack_id}: {e}")
        
        if user:
            # Update existing user
            if email is not None:
                user.email = email
            if display_name is not None:
                user.display_name = display_name
            if real_name is not None:
                user.real_name = real_name
            user.is_bot = is_bot
            user.updated_at = datetime.utcnow()
            logger.debug(f"Updated existing user {slack_id}")
        else:
            # Create new user
            user = User(
                slack_id=slack_id,
                email=email,
                display_name=display_name,
                real_name=real_name,
                is_bot=is_bot,
            )
            self.db.add(user)
            logger.info(f"Created new user {slack_id} with display_name: {display_name}")
        
        self.db.flush()  # Get the ID without committing
        return user

    def create_or_update_channel(
        self,
        slack_id: str,
        name: Optional[str] = None,
        is_private: bool = False,
        is_archived: bool = False,
    ) -> Channel:
        """Create a new channel or update existing channel information."""
        channel = self.db.query(Channel).filter(Channel.slack_id == slack_id).first()
        
        if channel:
            # Update existing channel
            if name is not None:
                channel.name = name
            channel.is_private = is_private
            channel.is_archived = is_archived
            channel.updated_at = datetime.utcnow()
        else:
            # Create new channel
            channel = Channel(
                slack_id=slack_id,
                name=name,
                is_private=is_private,
                is_archived=is_archived,
            )
            self.db.add(channel)
        
        self.db.flush()
        return channel

    def track_emoji_usage(
        self,
        user_slack_id: str,
        emoji_name: str,
        usage_type: str,
        channel_slack_id: Optional[str] = None,
        message_ts: Optional[str] = None,
        message_text: Optional[str] = None,
        target_user_slack_id: Optional[str] = None,
    ) -> Optional[EmojiUsage]:
        """Track a single emoji usage event."""
        # Check if we should track this emoji
        emoji_score = config.get_emoji_score(emoji_name)
        if emoji_score == 0:
            logger.debug(f"Emoji '{emoji_name}' not configured for tracking")
            return None
        
        # Get or create user
        user = self.create_or_update_user(user_slack_id)
        
        # Get or create channel if provided
        channel = None
        if channel_slack_id:
            channel = self.create_or_update_channel(channel_slack_id)
        
        # Get target user for reactions and message mentions
        target_user = None
        if target_user_slack_id:
            target_user = self.create_or_update_user(target_user_slack_id)
        
        # Create emoji usage record
        usage = EmojiUsage(
            user_id=user.id,
            channel_id=channel.id if channel else None,
            emoji_name=emoji_name,
            emoji_score=emoji_score,
            usage_type=usage_type,
            message_ts=message_ts,
            message_text=message_text,
            target_user_id=target_user.id if target_user else None,
        )
        
        self.db.add(usage)
        
        # Update statistics
        self._update_emoji_stats(user.id, emoji_name, emoji_score, "given")
        
        # Update target user stats for reactions and message mentions
        if target_user:
            self._update_emoji_stats(target_user.id, emoji_name, emoji_score, "received")
        
        if target_user_slack_id:
            logger.info(
                f"Tracked emoji usage: {user_slack_id} sent {emoji_name} to {target_user_slack_id} "
                f"(score: {emoji_score}, type: {usage_type})"
            )
        else:
            logger.info(
                f"Tracked emoji usage: {user_slack_id} used {emoji_name} "
                f"(score: {emoji_score}, type: {usage_type})"
            )
        
        return usage

    def _update_emoji_stats(
        self, user_id: int, emoji_name: str, score: int, stat_type: str
    ) -> None:
        """Update aggregated emoji statistics."""
        stats = (
            self.db.query(EmojiStats)
            .filter(
                and_(EmojiStats.user_id == user_id, EmojiStats.emoji_name == emoji_name)
            )
            .first()
        )
        
        if not stats:
            stats = EmojiStats(
                user_id=user_id,
                emoji_name=emoji_name,
                given_count=0,
                given_score=0,
                received_count=0,
                received_score=0,
                first_used=datetime.utcnow(),
            )
            self.db.add(stats)
        
        # Update stats based on type
        if stat_type == "given":
            stats.given_count = (stats.given_count or 0) + 1
            stats.given_score = (stats.given_score or 0) + score
        elif stat_type == "received":
            stats.received_count = (stats.received_count or 0) + 1
            stats.received_score = (stats.received_score or 0) + score
        
        stats.last_used = datetime.utcnow()

    def get_user_stats(self, slack_id: str) -> Optional[Dict]:
        """Get comprehensive statistics for a user."""
        user = self.db.query(User).filter(User.slack_id == slack_id).first()
        if not user:
            return None
        
        # Get aggregated stats
        stats_query = (
            self.db.query(
                func.sum(EmojiStats.given_count).label("total_given_count"),
                func.sum(EmojiStats.given_score).label("total_given_score"),
                func.sum(EmojiStats.received_count).label("total_received_count"),
                func.sum(EmojiStats.received_score).label("total_received_score"),
            )
            .filter(EmojiStats.user_id == user.id)
            .first()
        )
        
        # Get top emojis given and received
        top_given = (
            self.db.query(EmojiStats)
            .filter(EmojiStats.user_id == user.id)
            .filter(EmojiStats.given_count > 0)
            .order_by(desc(EmojiStats.given_score))
            .limit(10)
            .all()
        )
        
        top_received = (
            self.db.query(EmojiStats)
            .filter(EmojiStats.user_id == user.id)
            .filter(EmojiStats.received_count > 0)
            .order_by(desc(EmojiStats.received_score))
            .limit(10)
            .all()
        )
        
        return {
            "user": {
                "slack_id": user.slack_id,
                "display_name": user.display_name,
                "real_name": user.real_name,
                "email": user.email,
            },
            "totals": {
                "given_count": stats_query.total_given_count or 0,
                "given_score": stats_query.total_given_score or 0,
                "received_count": stats_query.total_received_count or 0,
                "received_score": stats_query.total_received_score or 0,
            },
            "top_given": [
                {
                    "emoji": stat.emoji_name,
                    "count": stat.given_count,
                    "score": stat.given_score,
                }
                for stat in top_given
            ],
            "top_received": [
                {
                    "emoji": stat.emoji_name,
                    "count": stat.received_count,
                    "score": stat.received_score,
                }
                for stat in top_received
            ],
        }

    def get_leaderboard(
        self, sort_by: str = "received_score", limit: int = 50
    ) -> List[Dict]:
        """Get leaderboard data sorted by various metrics."""
        valid_sort_options = [
            "received_score",
            "received_count",
            "given_score",
            "given_count",
        ]
        
        if sort_by not in valid_sort_options:
            sort_by = "received_score"
        
        # Map sort_by to aggregation
        if sort_by == "received_score":
            sort_field = func.sum(EmojiStats.received_score)
        elif sort_by == "received_count":
            sort_field = func.sum(EmojiStats.received_count)
        elif sort_by == "given_score":
            sort_field = func.sum(EmojiStats.given_score)
        else:  # given_count
            sort_field = func.sum(EmojiStats.given_count)
        
        results = (
            self.db.query(
                User,
                func.sum(EmojiStats.given_count).label("total_given_count"),
                func.sum(EmojiStats.given_score).label("total_given_score"),
                func.sum(EmojiStats.received_count).label("total_received_count"),
                func.sum(EmojiStats.received_score).label("total_received_score"),
            )
            .join(EmojiStats, User.id == EmojiStats.user_id)
            .group_by(User.id)
            .order_by(desc(sort_field))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "rank": idx + 1,
                "user": {
                    "slack_id": result.User.slack_id,
                    "display_name": result.User.display_name,
                    "real_name": result.User.real_name,
                },
                "stats": {
                    "given_count": result.total_given_count or 0,
                    "given_score": result.total_given_score or 0,
                    "received_count": result.total_received_count or 0,
                    "received_score": result.total_received_score or 0,
                },
            }
            for idx, result in enumerate(results)
        ]

    def get_user_history(
        self, slack_id: str, limit: int = 100, offset: int = 0
    ) -> Optional[Dict]:
        """Get recent emoji usage history for a user."""
        user = self.db.query(User).filter(User.slack_id == slack_id).first()
        if not user:
            return None
        
        history = (
            self.db.query(EmojiUsage)
            .filter(EmojiUsage.user_id == user.id)
            .order_by(desc(EmojiUsage.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        total_count = (
            self.db.query(func.count(EmojiUsage.id))
            .filter(EmojiUsage.user_id == user.id)
            .scalar()
        )
        
        return {
            "user": {
                "slack_id": user.slack_id,
                "display_name": user.display_name,
            },
            "history": [
                {
                    "emoji": usage.emoji_name,
                    "score": usage.emoji_score,
                    "type": usage.usage_type,
                    "timestamp": usage.created_at.isoformat(),
                }
                for usage in history
            ],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count,
            },
        }

    def extract_emojis_from_text(self, text: str) -> List[str]:
        """Extract emoji names from message text."""
        # Find all emojis in format :emoji_name:
        emoji_pattern = r":([a-zA-Z0-9_+-]+):"
        return re.findall(emoji_pattern, text)

    def extract_user_mentions(self, text: str, event_payload: Optional[Dict[str, Any]] = None) -> List[str]:
        """Extract user IDs from Slack message text and event payload.
        
        Handles multiple sources:
        1. Slack API format in text: <@USER_ID> or <@USER_ID|display_name>
        2. Event payload blocks/elements (for rich text)
        3. Display format: @username (attempts to resolve via Slack API)
        """
        user_ids = []
        
        # Method 1: Extract from event payload blocks (most reliable)
        if event_payload:
            payload_mentions = self._extract_mentions_from_payload(event_payload)
            user_ids.extend(payload_mentions)
            logger.debug(f'Payload mentions: {payload_mentions}')
        
        # Method 2: Extract Slack's internal format <@USER_ID> from text
        slack_mention_pattern = r"<@([A-Z0-9]+)(?:\|[^>]+)?>"
        slack_mentions = re.findall(slack_mention_pattern, text)
        user_ids.extend(slack_mentions)
        
        # Method 3: Extract display format @username and try to resolve them
        display_mention_pattern = r"@([a-zA-Z0-9._-]+)"
        display_mentions = re.findall(display_mention_pattern, text)
        
        # Remove display mentions that are part of slack mentions (avoid duplicates)
        text_without_slack_mentions = re.sub(slack_mention_pattern, "", text)
        display_mentions = re.findall(display_mention_pattern, text_without_slack_mentions)
        
        # Try to resolve display names to user IDs if we have a web client
        if display_mentions and self.web_client:
            resolved_ids = self._resolve_display_names_to_user_ids(display_mentions)
            user_ids.extend(resolved_ids)
        
        # Remove duplicates while preserving order
        unique_user_ids = list(dict.fromkeys(user_ids))
        
        logger.debug(f'Slack mentions: {slack_mentions}')
        logger.debug(f'Display mentions: {display_mentions}')
        logger.debug(f'Final user IDs: {unique_user_ids}')
        
        return unique_user_ids

    def _extract_mentions_from_payload(self, payload: Dict[str, Any]) -> List[str]:
        """Extract user mentions from Slack event payload blocks/elements."""
        user_ids = []
        
        try:
            # Check if payload has blocks (rich text format)
            blocks = payload.get("blocks", [])
            for block in blocks:
                if block.get("type") == "rich_text":
                    elements = block.get("elements", [])
                    for element in elements:
                        if element.get("type") == "rich_text_section":
                            section_elements = element.get("elements", [])
                            for section_element in section_elements:
                                if section_element.get("type") == "user":
                                    user_id = section_element.get("user_id")
                                    if user_id:
                                        user_ids.append(user_id)
            
            # Also check for mentions in other possible locations
            # Some Slack events might have user mentions in different structures
            if "mentions" in payload:
                mentions = payload["mentions"]
                if isinstance(mentions, list):
                    for mention in mentions:
                        if isinstance(mention, dict) and "user" in mention:
                            user_ids.append(mention["user"])
                        elif isinstance(mention, str):
                            user_ids.append(mention)
            
            # Check for user_mentions field (if it exists)
            if "user_mentions" in payload:
                user_mentions = payload["user_mentions"]
                if isinstance(user_mentions, list):
                    user_ids.extend(user_mentions)
        
        except Exception as e:
            logger.warning(f"Error extracting mentions from payload: {e}")
        
        return user_ids

    def _resolve_display_names_to_user_ids(self, display_names: List[str]) -> List[str]:
        """Resolve display names to Slack user IDs using the Slack API."""
        resolved_ids = []
        
        try:
            # Get all users from the workspace
            response = self.web_client.users_list(limit=1000)
            if not response.get("ok"):
                logger.warning("Failed to fetch users list from Slack API")
                return resolved_ids
            
            users = response.get("members", [])
            
            # Create lookup maps for different name formats
            username_to_id = {}  # Slack username (without @)
            display_name_to_id = {}  # Display name
            real_name_to_id = {}  # Real name
            
            for user in users:
                if user.get("deleted") or user.get("is_bot"):
                    continue
                    
                user_id = user.get("id")
                username = user.get("name", "").lower()
                profile = user.get("profile", {})
                display_name = profile.get("display_name", "").lower()
                real_name = profile.get("real_name", "").lower()
                
                if user_id and username:
                    username_to_id[username] = user_id
                if user_id and display_name:
                    display_name_to_id[display_name] = user_id
                if user_id and real_name:
                    real_name_to_id[real_name] = user_id
            
            # Try to resolve each display name
            for name in display_names:
                name_lower = name.lower()
                user_id = None
                
                # Try different matching strategies
                if name_lower in username_to_id:
                    user_id = username_to_id[name_lower]
                elif name_lower in display_name_to_id:
                    user_id = display_name_to_id[name_lower]
                elif name_lower in real_name_to_id:
                    user_id = real_name_to_id[name_lower]
                else:
                    for real_name, uid in real_name_to_id.items():
                        if name_lower in real_name or real_name in name_lower:
                            user_id = uid
                            break
                
                if user_id:
                    resolved_ids.append(user_id)
                    logger.info(f"Resolved display name '{name}' to user ID '{user_id}'")
                else:
                    logger.warning(f"Could not resolve display name '{name}' to user ID")
        
        except Exception as e:
            logger.error(f"Error resolving display names to user IDs: {e}")
        
        return resolved_ids

    def ensure_users_exist(self, user_ids: List[str]) -> List[User]:
        """Ensure all mentioned users exist in the database, create them if they don't."""
        users = []
        
        for user_id in user_ids:
            try:
                # Try to get existing user
                user = self.db.query(User).filter(User.slack_id == user_id).first()
                
                if not user:
                    # User doesn't exist, create them by fetching from Slack API
                    logger.info(f"Creating new user from mention: {user_id}")
                    user = self.create_or_update_user(
                        slack_id=user_id,
                        fetch_from_slack=True
                    )
                
                if user:
                    users.append(user)
                    
            except Exception as e:
                logger.error(f"Error ensuring user {user_id} exists: {e}")
        
        return users

    def get_channel_stats(self, channel_slack_id: str) -> Optional[Dict]:
        """Get emoji statistics for a specific channel."""
        channel = (
            self.db.query(Channel).filter(Channel.slack_id == channel_slack_id).first()
        )
        if not channel:
            return None
        
        # Get total usage in this channel
        total_usage = (
            self.db.query(
                func.count(EmojiUsage.id).label("total_count"),
                func.sum(EmojiUsage.emoji_score).label("total_score"),
            )
            .filter(EmojiUsage.channel_id == channel.id)
            .first()
        )
        
        # Get top emojis in this channel
        top_emojis = (
            self.db.query(
                EmojiUsage.emoji_name,
                func.count(EmojiUsage.id).label("count"),
                func.sum(EmojiUsage.emoji_score).label("score"),
            )
            .filter(EmojiUsage.channel_id == channel.id)
            .group_by(EmojiUsage.emoji_name)
            .order_by(desc(func.sum(EmojiUsage.emoji_score)))
            .limit(10)
            .all()
        )
        
        # Get top users in this channel
        top_users = (
            self.db.query(
                User,
                func.count(EmojiUsage.id).label("count"),
                func.sum(EmojiUsage.emoji_score).label("score"),
            )
            .join(EmojiUsage, User.id == EmojiUsage.user_id)
            .filter(EmojiUsage.channel_id == channel.id)
            .group_by(User.id)
            .order_by(desc(func.sum(EmojiUsage.emoji_score)))
            .limit(10)
            .all()
        )
        
        return {
            "channel": {
                "slack_id": channel.slack_id,
                "name": channel.name,
                "is_private": channel.is_private,
            },
            "totals": {
                "total_count": total_usage.total_count or 0,
                "total_score": total_usage.total_score or 0,
            },
            "top_emojis": [
                {
                    "emoji": emoji.emoji_name,
                    "count": emoji.count,
                    "score": emoji.score,
                }
                for emoji in top_emojis
            ],
            "top_users": [
                {
                    "user": {
                        "slack_id": result.User.slack_id,
                        "display_name": result.User.display_name,
                    },
                    "count": result.count,
                    "score": result.score,
                }
                for result in top_users
            ],
        }