"""Slack event listener for emoji tracking."""

import json
import logging
import re
from typing import Any, Dict, Optional

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from src.services.emoji_tracker import emoji_tracker
from src.utils.config import config

logger = logging.getLogger(__name__)


class SlackEventListener:
    """Slack event listener for tracking emoji usage."""

    def __init__(self) -> None:
        """Initialize the Slack event listener."""
        self.web_client = WebClient(token=config.slack_bot_token)
        self.socket_client = SocketModeClient(
            app_token=config.slack_app_token,
            web_client=self.web_client,
        )
        
        # Register event handlers
        self.socket_client.socket_mode_request_listeners.append(self._handle_socket_mode_request)
        
        # Emoji pattern for finding emojis in messages
        self.emoji_pattern = re.compile(r':([a-zA-Z0-9_+-]+):')

    def start(self) -> None:
        """Start listening for Slack events."""
        logger.info("Starting Slack event listener...")
        try:
            self.socket_client.connect()
            logger.info("Slack event listener started successfully")
        except Exception as e:
            logger.error(f"Failed to start Slack event listener: {e}")
            raise

    def stop(self) -> None:
        """Stop the Slack event listener."""
        logger.info("Stopping Slack event listener...")
        try:
            self.socket_client.disconnect()
            logger.info("Slack event listener stopped")
        except Exception as e:
            logger.error(f"Error stopping Slack event listener: {e}")

    def _handle_socket_mode_request(self, client: SocketModeClient, req: SocketModeRequest) -> None:
        """Handle incoming socket mode requests."""
        try:
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Process the event
            if req.type == "events_api":
                self._handle_events_api(req.payload)
            elif req.type == "slash_commands":
                self._handle_slash_command(req.payload)
            else:
                logger.debug(f"Unhandled request type: {req.type}")
                
        except Exception as e:
            logger.error(f"Error handling socket mode request: {e}")

    def _handle_events_api(self, payload: Dict[str, Any]) -> None:
        """Handle Events API payloads."""
        event = payload.get("event", {})
        event_type = event.get("type")
        
        if event_type == "reaction_added":
            self._handle_reaction_added(event)
        elif event_type == "reaction_removed":
            self._handle_reaction_removed(event)
        elif event_type == "message":
            self._handle_message(event)
        elif event_type == "app_mention":
            self._handle_app_mention(event)
        else:
            logger.debug(f"Unhandled event type: {event_type}")

    def _handle_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events."""
        try:
            # Extract event data
            emoji_name = event.get("reaction")
            giver_slack_id = event.get("user")
            channel_id = event.get("item", {}).get("channel")
            message_ts = event.get("item", {}).get("ts")
            reaction_ts = event.get("event_ts")
            
            if not emoji_name or not giver_slack_id:
                logger.warning("Missing required data in reaction_added event")
                return
            
            # Get the original message to find the receiver
            receiver_slack_id = self._get_message_author(channel_id, message_ts)
            
            # Update user info
            self._update_user_info(giver_slack_id)
            if receiver_slack_id:
                self._update_user_info(receiver_slack_id)
            
            # Track the emoji reaction
            emoji_tracker.track_emoji_reaction(
                giver_slack_id=giver_slack_id,
                receiver_slack_id=receiver_slack_id,
                emoji_name=emoji_name,
                channel_id=channel_id,
                message_ts=message_ts,
                reaction_ts=reaction_ts,
                context=f"Reaction added in channel {channel_id}",
            )
            
        except Exception as e:
            logger.error(f"Error handling reaction_added event: {e}")

    def _handle_reaction_removed(self, event: Dict[str, Any]) -> None:
        """Handle reaction_removed events."""
        # For now, we only track additions, not removals
        # This could be extended to remove points or track removal events
        logger.debug(f"Reaction removed: {event.get('reaction')} by {event.get('user')}")

    def _handle_message(self, event: Dict[str, Any]) -> None:
        """Handle message events to find emojis in message text."""
        try:
            # Skip bot messages and messages without text
            if event.get("bot_id") or not event.get("text"):
                return
            
            sender_slack_id = event.get("user")
            channel_id = event.get("channel")
            message_ts = event.get("ts")
            text = event.get("text", "")
            
            if not sender_slack_id:
                return
            
            # Find emojis in the message text
            emojis = self.emoji_pattern.findall(text)
            
            if emojis:
                # Update user info
                self._update_user_info(sender_slack_id)
                
                # Track each emoji found in the message
                for emoji_name in emojis:
                    emoji_tracker.track_emoji_message(
                        sender_slack_id=sender_slack_id,
                        emoji_name=emoji_name,
                        channel_id=channel_id,
                        message_ts=message_ts,
                        context=f"Emoji in message: {text[:100]}...",
                    )
            
        except Exception as e:
            logger.error(f"Error handling message event: {e}")

    def _handle_app_mention(self, event: Dict[str, Any]) -> None:
        """Handle app mention events."""
        # This could be used for bot commands or interactions
        logger.debug(f"App mentioned by {event.get('user')}: {event.get('text')}")

    def _handle_slash_command(self, payload: Dict[str, Any]) -> None:
        """Handle slash command events."""
        # This could be used for slash commands like /emoji-stats
        command = payload.get("command")
        user_id = payload.get("user_id")
        logger.debug(f"Slash command {command} from {user_id}")

    def _get_message_author(self, channel_id: str, message_ts: str) -> Optional[str]:
        """Get the author of a message."""
        try:
            # Get message details from Slack API
            response = self.web_client.conversations_history(
                channel=channel_id,
                latest=message_ts,
                limit=1,
                inclusive=True,
            )
            
            if response["ok"] and response["messages"]:
                message = response["messages"][0]
                return message.get("user")
            
        except Exception as e:
            logger.error(f"Error getting message author: {e}")
        
        return None

    def _update_user_info(self, slack_id: str) -> None:
        """Update user information from Slack API."""
        try:
            # Get user info from Slack API
            response = self.web_client.users_info(user=slack_id)
            
            if response["ok"]:
                user = response["user"]
                profile = user.get("profile", {})
                
                # Extract user information
                email = profile.get("email")
                display_name = profile.get("display_name")
                real_name = profile.get("real_name")
                
                # Update user in database
                emoji_tracker.create_or_update_user(
                    slack_id=slack_id,
                    email=email,
                    display_name=display_name,
                    real_name=real_name,
                )
                
        except Exception as e:
            logger.error(f"Error updating user info for {slack_id}: {e}")

    def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the bot."""
        try:
            response = self.web_client.auth_test()
            if response["ok"]:
                return {
                    "user_id": response["user_id"],
                    "team_id": response["team_id"],
                    "team": response["team"],
                    "url": response["url"],
                }
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
        
        return None

    def test_connection(self) -> bool:
        """Test the Slack connection."""
        try:
            response = self.web_client.auth_test()
            return response["ok"]
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False


# Global Slack event listener instance - initialized lazily
slack_listener = None


def get_slack_listener() -> SlackEventListener:
    """Get the global Slack event listener instance."""
    global slack_listener
    if slack_listener is None:
        slack_listener = SlackEventListener()
    return slack_listener