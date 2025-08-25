#!/usr/bin/env python3
"""
Main entry point for the Slack Emoji Tracker application.

This script can run different components of the system:
- API server (default)
- Slack event listener
- Database setup
"""

import argparse
import logging
import sys
import time
from typing import NoReturn

from src.api.main import app
from src.database.connection import db_manager
from src.slack.event_listener import get_slack_listener
from src.utils.config import config


def setup_logging() -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_api() -> NoReturn:
    """Run the FastAPI server."""
    import uvicorn
    
    print("Starting Slack Emoji Tracker API...")
    uvicorn.run(
        "src.api.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )


def run_slack_listener() -> NoReturn:
    """Run the Slack event listener."""
    print("Starting Slack event listener...")
    
    listener = get_slack_listener()
    try:
        listener.start()
        print("Slack event listener started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Slack event listener...")
        listener.stop()
        sys.exit(0)


def setup_database() -> None:
    """Setup the database (create tables)."""
    print("Setting up database...")
    
    # Test connection
    if not db_manager.test_connection():
        print("ERROR: Cannot connect to database!")
        sys.exit(1)
    
    # Create tables
    try:
        db_manager.create_tables()
        print("Database setup completed successfully!")
    except Exception as e:
        print(f"ERROR: Database setup failed: {e}")
        sys.exit(1)


def test_connections() -> None:
    """Test all system connections."""
    print("Testing system connections...")
    
    # Test database
    print("Testing database connection...")
    if db_manager.test_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
    
    # Test Slack
    print("Testing Slack connection...")
    try:
        listener = get_slack_listener()
        if listener.test_connection():
            print("✓ Slack connection successful")
        else:
            print("✗ Slack connection failed")
    except Exception as e:
        print(f"✗ Slack connection error: {e}")
    
    # Test configuration
    print("Testing configuration...")
    try:
        emoji_count = len(config.emoji_config.get("emojis", {}))
        print(f"✓ Configuration loaded ({emoji_count} emojis configured)")
    except Exception as e:
        print(f"✗ Configuration error: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Slack Emoji Tracker - Track and analyze Slack emoji usage"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # API command
    subparsers.add_parser("api", help="Run the REST API server")
    
    # Slack listener command
    subparsers.add_parser("slack", help="Run the Slack event listener")
    
    # Database setup command
    subparsers.add_parser("setup-db", help="Setup the database (create tables)")
    
    # Test connections command
    subparsers.add_parser("test", help="Test all system connections")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.command == "api":
        run_api()
    elif args.command == "slack":
        run_slack_listener()
    elif args.command == "setup-db":
        setup_database()
    elif args.command == "test":
        test_connections()
    else:
        # Default to API
        print("No command specified, running API server...")
        run_api()


if __name__ == "__main__":
    main()