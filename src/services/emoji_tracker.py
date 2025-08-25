"""Core emoji tracking service."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.models.database import Channel, EmojiStats, EmojiUsage, User
from src.utils.config import config

logger = logging.getLogger(__name__)


class EmojiTrackerService:
    """Service for tracking emoji usage and managing statistics."""

    def __init__(self) -> None:
        """Initialize the emoji tracker service."""
        self.config = config

    def track_emoji_reaction(
        self,
        giver_slack_id: str,
        receiver_slack_id: Optional[str],
        emoji_name: str,
        channel_id: Optional[str] = None,
        message_ts: Optional[str] = None,
        reaction_ts: Optional[str] = None,
        context: Optional[str] = None,
    ) -> bool:
        """
        Track an emoji reaction event.
        
        Args:
            giver_slack_id: Slack ID of the user who gave the emoji
            receiver_slack_id: Slack ID of the user who received the emoji
            emoji_name: Name of the emoji
            channel_id: Channel where the reaction occurred
            message_ts: Timestamp of the original message
            reaction_ts: Timestamp of the reaction
            context: Additional context information
            
        Returns:
            bool: True if tracking was successful, False otherwise
        """
        # Normalize emoji name
        emoji_name = self._normalize_emoji_name(emoji_name)
        
        # Check if this emoji should be tracked
        if not self.config.is_tracked_emoji(emoji_name):
            logger.debug(f"Emoji '{emoji_name}' is not configured for tracking")
            return False
        
        # Get emoji score
        score = self.config.get_emoji_score(emoji_name)
        
        session = db_manager.get_session()
        try:
            # Create emoji usage record
            usage = EmojiUsage(
                giver_slack_id=giver_slack_id,
                receiver_slack_id=receiver_slack_id,
                emoji_name=emoji_name,
                emoji_score=score,
                channel_id=channel_id,
                message_ts=message_ts,
                reaction_ts=reaction_ts,
                event_type="reaction",
                context=context,
            )
            
            session.add(usage)
            session.commit()
            
            # Update statistics
            self._update_user_stats(session, giver_slack_id, receiver_slack_id, score, emoji_name)
            
            logger.info(
                f"Tracked emoji reaction: {emoji_name} "
                f"from {giver_slack_id} to {receiver_slack_id} "
                f"(score: {score})"
            )
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error tracking emoji reaction: {e}")
            return False
        finally:
            db_manager.close_session(session)

    def track_emoji_message(
        self,
        sender_slack_id: str,
        emoji_name: str,
        channel_id: Optional[str] = None,
        message_ts: Optional[str] = None,
        context: Optional[str] = None,
    ) -> bool:
        """
        Track an emoji used in a message.
        
        Args:
            sender_slack_id: Slack ID of the user who sent the message
            emoji_name: Name of the emoji
            channel_id: Channel where the message was sent
            message_ts: Timestamp of the message
            context: Additional context information
            
        Returns:
            bool: True if tracking was successful, False otherwise
        """
        # Normalize emoji name
        emoji_name = self._normalize_emoji_name(emoji_name)
        
        # Check if this emoji should be tracked
        if not self.config.is_tracked_emoji(emoji_name):
            logger.debug(f"Emoji '{emoji_name}' is not configured for tracking")
            return False
        
        # Get emoji score
        score = self.config.get_emoji_score(emoji_name)
        
        session = db_manager.get_session()
        try:
            # Create emoji usage record
            usage = EmojiUsage(
                giver_slack_id=sender_slack_id,
                receiver_slack_id=None,  # No receiver for message emojis
                emoji_name=emoji_name,
                emoji_score=score,
                channel_id=channel_id,
                message_ts=message_ts,
                event_type="message",
                context=context,
            )
            
            session.add(usage)
            session.commit()
            
            # Update statistics (sender gives to themselves for message emojis)
            self._update_user_stats(session, sender_slack_id, None, score, emoji_name)
            
            logger.info(
                f"Tracked emoji message: {emoji_name} "
                f"from {sender_slack_id} "
                f"(score: {score})"
            )
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error tracking emoji message: {e}")
            return False
        finally:
            db_manager.close_session(session)

    def get_user_stats(self, slack_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific user.
        
        Args:
            slack_id: Slack ID of the user
            
        Returns:
            Dict with user statistics or None if user not found
        """
        session = db_manager.get_session()
        try:
            stats = session.query(EmojiStats).filter(
                EmojiStats.user_slack_id == slack_id
            ).first()
            
            if not stats:
                return None
            
            return {
                "slack_id": stats.user_slack_id,
                "total_given_score": stats.total_given_score,
                "total_received_score": stats.total_received_score,
                "total_given_count": stats.total_given_count,
                "total_received_count": stats.total_received_count,
                "most_given_emoji": stats.most_given_emoji,
                "most_received_emoji": stats.most_received_emoji,
                "last_activity": stats.last_activity,
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
        finally:
            db_manager.close_session(session)

    def get_leaderboard(self, limit: int = 10, order_by: str = "total_received_score") -> List[Dict]:
        """
        Get emoji usage leaderboard.
        
        Args:
            limit: Maximum number of users to return
            order_by: Field to order by (total_received_score, total_given_score, etc.)
            
        Returns:
            List of user statistics ordered by the specified field
        """
        session = db_manager.get_session()
        try:
            # Build query based on order_by parameter
            order_field = getattr(EmojiStats, order_by, EmojiStats.total_received_score)
            
            stats = session.query(EmojiStats).order_by(
                order_field.desc()
            ).limit(limit).all()
            
            return [
                {
                    "slack_id": stat.user_slack_id,
                    "total_given_score": stat.total_given_score,
                    "total_received_score": stat.total_received_score,
                    "total_given_count": stat.total_given_count,
                    "total_received_count": stat.total_received_count,
                    "most_given_emoji": stat.most_given_emoji,
                    "most_received_emoji": stat.most_received_emoji,
                    "last_activity": stat.last_activity,
                }
                for stat in stats
            ]
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
        finally:
            db_manager.close_session(session)

    def create_or_update_user(
        self,
        slack_id: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        real_name: Optional[str] = None,
    ) -> bool:
        """
        Create or update a user record.
        
        Args:
            slack_id: Slack ID of the user
            email: User's email address
            display_name: User's display name
            real_name: User's real name
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = db_manager.get_session()
        try:
            # Check if user exists
            user = session.query(User).filter(User.slack_id == slack_id).first()
            
            if user:
                # Update existing user
                if email:
                    user.email = email
                if display_name:
                    user.display_name = display_name
                if real_name:
                    user.real_name = real_name
                user.updated_at = datetime.utcnow()
            else:
                # Create new user
                user = User(
                    slack_id=slack_id,
                    email=email,
                    display_name=display_name,
                    real_name=real_name,
                )
                session.add(user)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating/updating user: {e}")
            return False
        finally:
            db_manager.close_session(session)

    def _normalize_emoji_name(self, emoji_name: str) -> str:
        """Normalize emoji name based on configuration."""
        # Remove colons if present
        emoji_name = emoji_name.strip(":")
        
        # Apply case sensitivity settings
        if not self.config.case_sensitive:
            emoji_name = emoji_name.lower()
        
        return emoji_name

    def _update_user_stats(
        self,
        session: Session,
        giver_slack_id: str,
        receiver_slack_id: Optional[str],
        score: int,
        emoji_name: str,
    ) -> None:
        """Update user statistics after an emoji event."""
        # Update giver stats
        self._update_single_user_stats(
            session, giver_slack_id, given_score=score, given_count=1, 
            given_emoji=emoji_name
        )
        
        # Update receiver stats (if applicable)
        if receiver_slack_id and receiver_slack_id != giver_slack_id:
            self._update_single_user_stats(
                session, receiver_slack_id, received_score=score, 
                received_count=1, received_emoji=emoji_name
            )

    def _update_single_user_stats(
        self,
        session: Session,
        slack_id: str,
        given_score: int = 0,
        received_score: int = 0,
        given_count: int = 0,
        received_count: int = 0,
        given_emoji: Optional[str] = None,
        received_emoji: Optional[str] = None,
    ) -> None:
        """Update statistics for a single user."""
        # Get or create user stats
        stats = session.query(EmojiStats).filter(
            EmojiStats.user_slack_id == slack_id
        ).first()
        
        if not stats:
            stats = EmojiStats(user_slack_id=slack_id)
            session.add(stats)
        
        # Update totals
        stats.total_given_score += given_score
        stats.total_received_score += received_score
        stats.total_given_count += given_count
        stats.total_received_count += received_count
        
        # Update most used emojis (simplified - could be more sophisticated)
        if given_emoji:
            stats.most_given_emoji = given_emoji
        if received_emoji:
            stats.most_received_emoji = received_emoji
        
        # Update last activity
        stats.last_activity = datetime.utcnow()
        stats.updated_at = datetime.utcnow()
        
        session.commit()


# Global emoji tracker service instance
emoji_tracker = EmojiTrackerService()