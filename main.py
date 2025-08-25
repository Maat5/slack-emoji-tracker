#!/usr/bin/env python3
"""
Main entry point for the Slack Emoji Tracker application.

This script provides multiple run modes:
- api: Start the REST API server
- slack: Start the Slack event listener
- setup-db: Initialize the database and run migrations
- test: Test all connections and configurations
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from slack_emoji_tracker.config import config
from slack_emoji_tracker.database import create_tables, check_database_connection
from slack_emoji_tracker.slack_service import SlackService


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def run_api() -> None:
    """Start the FastAPI REST API server."""
    import uvicorn
    
    print("🚀 Starting Slack Emoji Tracker API...")
    print(f"📡 Server will be available at http://{config.api_host}:{config.api_port}")
    print(f"📚 API documentation at http://{config.api_host}:{config.api_port}/docs")
    
    uvicorn.run(
        "slack_emoji_tracker.api:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.environment == "development",
        log_level=config.log_level.lower(),
    )


async def run_slack_listener() -> None:
    """Start the Slack event listener."""
    print("🔄 Starting Slack event listener...")
    
    try:
        slack_service = SlackService()
        await slack_service.start()
        
        print("✅ Slack listener started successfully")
        print("📡 Listening for emoji events...")
        print("Press Ctrl+C to stop")
        
        # Keep the listener running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping Slack listener...")
            await slack_service.stop()
            print("✅ Slack listener stopped")
            
    except Exception as e:
        print(f"❌ Failed to start Slack listener: {e}")
        sys.exit(1)


async def setup_database() -> None:
    """Initialize the database and run migrations."""
    print("🗄️  Setting up database...")
    
    # Check database connection
    if not check_database_connection():
        print("❌ Database connection failed!")
        print("Make sure PostgreSQL is running and DATABASE_URL is correct")
        sys.exit(1)
    
    print("✅ Database connection successful")
    
    # Create tables
    try:
        create_tables()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Failed to create database tables: {e}")
        sys.exit(1)
    
    # Try to sync some initial data if Slack is configured
    try:
        config.validate_required_config()
        slack_service = SlackService()
        
        print("👥 Syncing users from Slack...")
        user_count = await slack_service.sync_users(limit=100)
        print(f"✅ Synced {user_count} users")
        
        print("📢 Syncing channels from Slack...")
        channel_count = await slack_service.sync_channels(limit=100)
        print(f"✅ Synced {channel_count} channels")
        
    except Exception as e:
        print(f"⚠️  Could not sync Slack data: {e}")
        print("Database setup complete, but Slack sync failed")
        print("Make sure SLACK_BOT_TOKEN and SLACK_APP_TOKEN are configured")


async def test_connections() -> None:
    """Test all connections and configurations."""
    print("🧪 Testing connections and configuration...")
    
    # Test database connection
    print("\n🗄️  Testing database connection...")
    if check_database_connection():
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
        return
    
    # Test emoji configuration
    print("\n😀 Testing emoji configuration...")
    try:
        emoji_count = len(config.emoji_config["emojis"])
        default_score = config.emoji_config["settings"]["default_score"]
        print(f"✅ Emoji config loaded: {emoji_count} emojis, default score: {default_score}")
        
        # Test a few emojis
        test_emojis = ["thumbsup", "heart", "nonexistent"]
        for emoji in test_emojis:
            score = config.get_emoji_score(emoji)
            print(f"   {emoji}: score={score}")
            
    except Exception as e:
        print(f"❌ Emoji configuration error: {e}")
        return
    
    # Test Slack connection
    print("\n📱 Testing Slack connection...")
    try:
        config.validate_required_config()
        slack_service = SlackService()
        
        if await slack_service.test_connection():
            print("✅ Slack connection successful")
        else:
            print("❌ Slack connection failed")
            
    except Exception as e:
        print(f"❌ Slack configuration error: {e}")
        print("Make sure SLACK_BOT_TOKEN and SLACK_APP_TOKEN are set in .env")
    
    print("\n🎉 Connection tests completed!")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Slack Emoji Tracker - Multi-mode application"
    )
    parser.add_argument(
        "mode",
        choices=["api", "slack", "setup-db", "test"],
        help="Run mode: api (REST API), slack (event listener), setup-db (database setup), test (connection tests)",
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    print("🎯 Slack Emoji Tracker")
    print(f"🔧 Environment: {config.environment}")
    print(f"📊 Log level: {config.log_level}")
    print()
    
    # Run the appropriate mode
    try:
        if args.mode == "api":
            asyncio.run(run_api())
        elif args.mode == "slack":
            asyncio.run(run_slack_listener())
        elif args.mode == "setup-db":
            asyncio.run(setup_database())
        elif args.mode == "test":
            asyncio.run(test_connections())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()