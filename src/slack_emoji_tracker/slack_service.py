"""Slack integration service for real-time emoji tracking."""

import asyncio
import logging
from typing import Any, Dict, Optional

from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

from .config import config
from .database import get_db_session
from .service import EmojiService

logger = logging.getLogger(__name__)


class SlackService:
    """Service for handling Slack events and emoji tracking."""

    def __init__(self):
        """Initialize the Slack service."""
        config.validate_required_config()
        
        self.web_client = WebClient(token=config.slack_bot_token)
        self.socket_client = SocketModeClient(
            app_token=config.slack_app_token,
            web_client=self.web_client,
        )
        
        # Register event handlers
        self.socket_client.socket_mode_request_listeners.append(
            self._handle_socket_mode_request
        )

    async def start(self) -> None:
        """Start the Slack Socket Mode connection."""
        logger.info("Starting Slack Socket Mode connection...")
        
        try:
            # Test the connection first
            auth_response = await asyncio.to_thread(self.web_client.auth_test)
            logger.info(f"Connected to Slack as: {auth_response['user']}")
            
            # Start the socket mode client
            await asyncio.to_thread(self.socket_client.connect)
            logger.info("Slack Socket Mode connection established")
            
        except Exception as e:
            logger.error(f"Failed to start Slack service: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Slack Socket Mode connection."""
        logger.info("Stopping Slack Socket Mode connection...")
        try:
            await asyncio.to_thread(self.socket_client.disconnect)
            logger.info("Slack Socket Mode connection closed")
        except Exception as e:
            logger.error(f"Error stopping Slack service: {e}")

    def _handle_socket_mode_request(self, client: SocketModeClient, req: SocketModeRequest) -> None:
        """Handle incoming Socket Mode requests."""
        try:
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Process the event asynchronously
            if req.type == "events_api":
                asyncio.create_task(self._handle_event(req.payload))
                
        except Exception as e:
            logger.error(f"Error handling Socket Mode request: {e}")

    async def _handle_event(self, payload: Dict[str, Any]) -> None:
        """Handle Slack events."""
        event = payload.get("event", {})
        event_type = event.get("type")
        
        logger.debug(f"Received event: {event_type}")
        
        try:
            if event_type == "reaction_added":
                await self._handle_reaction_added(event)
            elif event_type == "message":
                await self._handle_message(event)
            elif event_type == "user_change":
                await self._handle_user_change(event)
            elif event_type == "channel_created" or event_type == "channel_rename":
                await self._handle_channel_change(event)
                
        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")

    async def _handle_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events."""
        user_id = event.get("user")
        reaction = event.get("reaction")
        item = event.get("item", {})
        
        if not user_id or not reaction:
            logger.warning("Missing user or reaction in reaction_added event")
            return
        
        # Get the target user (who received the reaction)
        target_user_id = None
        if item.get("type") == "message":
            channel_id = item.get("channel")
            message_ts = item.get("ts")
            
            # Try to get the message to find the author
            try:
                message_info = await asyncio.to_thread(
                    self.web_client.conversations_history,
                    channel=channel_id,
                    latest=message_ts,
                    limit=1,
                    inclusive=True,
                )
                
                messages = message_info.get("messages", [])
                if messages:
                    target_user_id = messages[0].get("user")
                    
            except Exception as e:
                logger.warning(f"Could not fetch message info: {e}")
        
        # Track the emoji usage
        with get_db_session() as db:
            emoji_service = EmojiService(db)
            emoji_service.track_emoji_usage(
                user_slack_id=user_id,
                emoji_name=reaction,
                usage_type="reaction",
                channel_slack_id=item.get("channel"),
                message_ts=item.get("ts"),
                target_user_slack_id=target_user_id,
            )

    async def _handle_message(self, event: Dict[str, Any]) -> None:
        """Handle message events to track emojis in message text."""
        user_id = event.get("user")
        text = event.get("text", "")
        channel = event.get("channel")
        ts = event.get("ts")
        
        # Skip bot messages and messages without text
        if not user_id or not text or event.get("subtype") == "bot_message":
            return
        
        # Extract emojis from the message text
        with get_db_session() as db:
            emoji_service = EmojiService(db)
            emojis = emoji_service.extract_emojis_from_text(text)
            
            # Track each emoji found in the message
            for emoji in emojis:
                emoji_service.track_emoji_usage(
                    user_slack_id=user_id,
                    emoji_name=emoji,
                    usage_type="message",
                    channel_slack_id=channel,
                    message_ts=ts,
                )

    async def _handle_user_change(self, event: Dict[str, Any]) -> None:
        """Handle user_change events to update user information."""
        user_data = event.get("user", {})
        user_id = user_data.get("id")
        
        if not user_id:
            return
        
        # Update user information
        with get_db_session() as db:
            emoji_service = EmojiService(db)
            profile = user_data.get("profile", {})
            
            emoji_service.create_or_update_user(
                slack_id=user_id,
                email=profile.get("email"),
                display_name=profile.get("display_name") or user_data.get("name"),
                real_name=profile.get("real_name"),
                is_bot=user_data.get("is_bot", False),
            )

    async def _handle_channel_change(self, event: Dict[str, Any]) -> None:
        """Handle channel creation and rename events."""
        channel_data = event.get("channel", {})
        channel_id = channel_data.get("id")
        
        if not channel_id:
            return
        
        # Update channel information
        with get_db_session() as db:
            emoji_service = EmojiService(db)
            
            emoji_service.create_or_update_channel(
                slack_id=channel_id,
                name=channel_data.get("name"),
                is_private=channel_data.get("is_private", False),
                is_archived=channel_data.get("is_archived", False),
            )

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from Slack API."""
        try:
            response = await asyncio.to_thread(
                self.web_client.users_info, user=user_id
            )
            return response.get("user")
        except Exception as e:
            logger.error(f"Error fetching user info for {user_id}: {e}")
            return None

    async def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information from Slack API."""
        try:
            response = await asyncio.to_thread(
                self.web_client.conversations_info, channel=channel_id
            )
            return response.get("channel")
        except Exception as e:
            logger.error(f"Error fetching channel info for {channel_id}: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test the Slack connection."""
        try:
            auth_response = await asyncio.to_thread(self.web_client.auth_test)
            logger.info(f"Slack connection test successful: {auth_response.get('user')}")
            return True
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False

    async def sync_users(self, limit: int = 1000) -> int:
        """Sync users from Slack workspace to database."""
        logger.info("Starting user synchronization...")
        synced_count = 0
        
        try:
            cursor = None
            with get_db_session() as db:
                emoji_service = EmojiService(db)
                
                while True:
                    # Get users from Slack API
                    users_response = await asyncio.to_thread(
                        self.web_client.users_list,
                        limit=min(limit, 200),  # Slack API limit
                        cursor=cursor,
                    )
                    
                    users = users_response.get("members", [])
                    if not users:
                        break
                    
                    # Process each user
                    for user_data in users:
                        if user_data.get("deleted"):
                            continue
                        
                        profile = user_data.get("profile", {})
                        emoji_service.create_or_update_user(
                            slack_id=user_data["id"],
                            email=profile.get("email"),
                            display_name=profile.get("display_name") or user_data.get("name"),
                            real_name=profile.get("real_name"),
                            is_bot=user_data.get("is_bot", False),
                        )
                        synced_count += 1
                    
                    # Check if there are more users
                    cursor = users_response.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
                    
                    # Check limit
                    if synced_count >= limit:
                        break
            
            logger.info(f"User synchronization completed: {synced_count} users synced")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error during user synchronization: {e}")
            raise

    async def sync_channels(self, limit: int = 1000) -> int:
        """Sync channels from Slack workspace to database."""
        logger.info("Starting channel synchronization...")
        synced_count = 0
        
        try:
            cursor = None
            with get_db_session() as db:
                emoji_service = EmojiService(db)
                
                while True:
                    # Get channels from Slack API
                    channels_response = await asyncio.to_thread(
                        self.web_client.conversations_list,
                        limit=min(limit, 200),  # Slack API limit
                        cursor=cursor,
                        types="public_channel,private_channel",
                    )
                    
                    channels = channels_response.get("channels", [])
                    if not channels:
                        break
                    
                    # Process each channel
                    for channel_data in channels:
                        emoji_service.create_or_update_channel(
                            slack_id=channel_data["id"],
                            name=channel_data.get("name"),
                            is_private=channel_data.get("is_private", False),
                            is_archived=channel_data.get("is_archived", False),
                        )
                        synced_count += 1
                    
                    # Check if there are more channels
                    cursor = channels_response.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
                    
                    # Check limit
                    if synced_count >= limit:
                        break
            
            logger.info(f"Channel synchronization completed: {synced_count} channels synced")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error during channel synchronization: {e}")
            raise