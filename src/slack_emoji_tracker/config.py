"""Configuration management for the Slack Emoji Tracker."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


class Config:
    """Configuration manager for the application."""

    def __init__(self) -> None:
        """Initialize configuration."""
        # Load environment variables
        load_dotenv()
        
        # Slack configuration
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        
        # Database configuration
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:password@localhost:5432/slack_emoji_tracker"
        )
        
        # API configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Load emoji configuration
        self.emoji_config = self._load_emoji_config()
    
    def _load_emoji_config(self) -> Dict[str, Any]:
        """Load emoji configuration from JSON file."""
        config_path = Path(__file__).parent.parent.parent / "config" / "emoji_config.json"
        
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default configuration if file not found
            return {
                "emojis": {
                    "thumbsup": {"score": 1, "description": "Positive reaction"}
                },
                "settings": {
                    "default_score": 1,
                    "track_all_emojis": False,
                    "case_sensitive": False
                }
            }
    
    def get_emoji_score(self, emoji_name: str) -> int:
        """Get the score for a specific emoji."""
        emoji_name = emoji_name.strip(":")
        if not self.emoji_config["settings"]["case_sensitive"]:
            emoji_name = emoji_name.lower()
        
        emoji_config = self.emoji_config["emojis"].get(emoji_name)
        if emoji_config:
            return emoji_config["score"]
        
        # Return default score if emoji not found and track_all_emojis is True
        if self.emoji_config["settings"]["track_all_emojis"]:
            return self.emoji_config["settings"]["default_score"]
        
        return 0  # Don't track this emoji
    
    def should_track_emoji(self, emoji_name: str) -> bool:
        """Check if an emoji should be tracked."""
        return self.get_emoji_score(emoji_name) > 0
    
    def validate_required_config(self) -> None:
        """Validate that required configuration is present."""
        missing = []
        
        if not self.slack_bot_token:
            missing.append("SLACK_BOT_TOKEN")
        if not self.slack_app_token:
            missing.append("SLACK_APP_TOKEN")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


# Global config instance
config = Config()