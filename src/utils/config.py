"""Configuration loader for the Slack emoji tracker."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


class Config:
    """Configuration manager for the application."""

    def __init__(self) -> None:
        """Initialize the configuration."""
        # Load environment variables
        load_dotenv()
        
        # Set base paths
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "config"
        
        # Load emoji configuration
        self._emoji_config: Optional[Dict[str, Any]] = None
    
    @property
    def emoji_config(self) -> Dict[str, Any]:
        """Get the emoji configuration."""
        if self._emoji_config is None:
            self._emoji_config = self._load_emoji_config()
        return self._emoji_config
    
    def _load_emoji_config(self) -> Dict[str, Any]:
        """Load emoji configuration from JSON file."""
        config_path = self.config_dir / "emoji_config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Emoji config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_emoji_score(self, emoji_name: str) -> int:
        """Get the score for a specific emoji."""
        emojis = self.emoji_config.get("emojis", {})
        emoji_data = emojis.get(emoji_name, {})
        
        if emoji_data:
            return emoji_data.get("score", self.default_score)
        
        # Return default score if emoji not configured
        return self.default_score
    
    def is_tracked_emoji(self, emoji_name: str) -> bool:
        """Check if an emoji is configured for tracking."""
        emojis = self.emoji_config.get("emojis", {})
        settings = self.emoji_config.get("settings", {})
        
        # If track_all_emojis is True, track everything
        if settings.get("track_all_emojis", False):
            return True
        
        # Otherwise, only track configured emojis
        return emoji_name in emojis
    
    @property
    def default_score(self) -> int:
        """Get the default score for unconfigured emojis."""
        settings = self.emoji_config.get("settings", {})
        return settings.get("default_score", 1)
    
    @property
    def case_sensitive(self) -> bool:
        """Get whether emoji names are case sensitive."""
        settings = self.emoji_config.get("settings", {})
        return settings.get("case_sensitive", False)
    
    # Slack Configuration
    @property
    def slack_bot_token(self) -> str:
        """Get Slack bot token."""
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            raise ValueError("SLACK_BOT_TOKEN environment variable is required")
        return token
    
    @property
    def slack_app_token(self) -> str:
        """Get Slack app token."""
        token = os.getenv("SLACK_APP_TOKEN")
        if not token:
            raise ValueError("SLACK_APP_TOKEN environment variable is required")
        return token
    
    @property
    def slack_signing_secret(self) -> str:
        """Get Slack signing secret."""
        secret = os.getenv("SLACK_SIGNING_SECRET")
        if not secret:
            raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
        return secret
    
    # Database Configuration
    @property
    def database_url(self) -> str:
        """Get database URL."""
        url = os.getenv("DATABASE_URL")
        if not url:
            # Construct from individual components
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            name = os.getenv("DB_NAME", "slack_emoji_tracker")
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "")
            url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        return url
    
    # API Configuration
    @property
    def api_host(self) -> str:
        """Get API host."""
        return os.getenv("API_HOST", "0.0.0.0")
    
    @property
    def api_port(self) -> int:
        """Get API port."""
        return int(os.getenv("API_PORT", "8000"))
    
    @property
    def debug(self) -> bool:
        """Get debug mode."""
        return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return os.getenv("LOG_LEVEL", "INFO").upper()


# Global configuration instance
config = Config()