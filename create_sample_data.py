#!/usr/bin/env python3
"""
Test script to populate the database with sample data for demonstration.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from slack_emoji_tracker.database import get_db_session
from slack_emoji_tracker.service import EmojiService


def create_sample_data():
    """Create sample data for testing the emoji tracker."""
    print("🔄 Creating sample data...")
    
    with get_db_session() as db:
        service = EmojiService(db)
        
        # Create some sample users
        print("👥 Creating sample users...")
        users = [
            ("U1234567890", "alice@example.com", "Alice", "Alice Johnson"),
            ("U1234567891", "bob@example.com", "Bob", "Bob Smith"),
            ("U1234567892", "charlie@example.com", "Charlie", "Charlie Brown"),
            ("U1234567893", "diana@example.com", "Diana", "Diana Prince"),
            ("U1234567894", "eve@example.com", "Eve", "Eve Wilson"),
        ]
        
        for slack_id, email, display_name, real_name in users:
            service.create_or_update_user(
                slack_id=slack_id,
                email=email,
                display_name=display_name,
                real_name=real_name,
            )
        
        # Create sample channels
        print("📢 Creating sample channels...")
        channels = [
            ("C1234567890", "general", False),
            ("C1234567891", "random", False),
            ("C1234567892", "dev-team", True),
            ("C1234567893", "announcements", False),
        ]
        
        for slack_id, name, is_private in channels:
            service.create_or_update_channel(
                slack_id=slack_id,
                name=name,
                is_private=is_private,
            )
        
        # Create sample emoji usage
        print("😀 Creating sample emoji usage...")
        
        # Alice gives reactions
        service.track_emoji_usage("U1234567890", "thumbsup", "reaction", "C1234567890", "1609459200.123", "U1234567891")
        service.track_emoji_usage("U1234567890", "heart", "reaction", "C1234567890", "1609459201.123", "U1234567891")
        service.track_emoji_usage("U1234567890", "fire", "reaction", "C1234567891", "1609459202.123", "U1234567892")
        service.track_emoji_usage("U1234567890", "rocket", "reaction", "C1234567891", "1609459203.123", "U1234567893")
        service.track_emoji_usage("U1234567890", "trophy", "reaction", "C1234567892", "1609459204.123", "U1234567894")
        
        # Bob gives reactions
        service.track_emoji_usage("U1234567891", "thumbsup", "reaction", "C1234567890", "1609459205.123", "U1234567890")
        service.track_emoji_usage("U1234567891", "heart", "reaction", "C1234567890", "1609459206.123", "U1234567892")
        service.track_emoji_usage("U1234567891", "fire", "reaction", "C1234567891", "1609459207.123", "U1234567893")
        service.track_emoji_usage("U1234567891", "star", "reaction", "C1234567891", "1609459208.123", "U1234567894")
        
        # Charlie gives reactions
        service.track_emoji_usage("U1234567892", "heart", "reaction", "C1234567890", "1609459209.123", "U1234567890")
        service.track_emoji_usage("U1234567892", "clap", "reaction", "C1234567890", "1609459210.123", "U1234567891")
        service.track_emoji_usage("U1234567892", "100", "reaction", "C1234567891", "1609459211.123", "U1234567893")
        service.track_emoji_usage("U1234567892", "muscle", "reaction", "C1234567891", "1609459212.123", "U1234567894")
        
        # Diana uses emojis in messages
        service.track_emoji_usage("U1234567893", "brain", "message", "C1234567892", "1609459213.123")
        service.track_emoji_usage("U1234567893", "fire", "message", "C1234567892", "1609459214.123")
        service.track_emoji_usage("U1234567893", "rocket", "message", "C1234567893", "1609459215.123")
        
        # Eve gives more reactions to create interesting leaderboard data
        service.track_emoji_usage("U1234567894", "trophy", "reaction", "C1234567890", "1609459216.123", "U1234567890")
        service.track_emoji_usage("U1234567894", "trophy", "reaction", "C1234567890", "1609459217.123", "U1234567891")
        service.track_emoji_usage("U1234567894", "rocket", "reaction", "C1234567891", "1609459218.123", "U1234567892")
        service.track_emoji_usage("U1234567894", "fire", "reaction", "C1234567891", "1609459219.123", "U1234567893")
        service.track_emoji_usage("U1234567894", "heart", "reaction", "C1234567892", "1609459220.123", "U1234567890")
        
        print("✅ Sample data created successfully!")
        print()
        print("📊 Summary:")
        print("- 5 users created")
        print("- 4 channels created")
        print("- 17 emoji usage events created")
        print()
        print("🎉 You can now test the API endpoints with real data!")


if __name__ == "__main__":
    create_sample_data()