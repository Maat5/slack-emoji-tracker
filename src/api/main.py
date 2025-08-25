"""FastAPI REST API for emoji tracking statistics."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.database.connection import db_manager
from src.services.emoji_tracker import emoji_tracker
from src.slack.event_listener import get_slack_listener
from src.utils.config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Slack Emoji Tracker API",
    description="API for tracking and querying Slack emoji usage statistics",
    version="0.1.0",
    debug=config.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API responses
class UserStats(BaseModel):
    """User statistics response model."""
    slack_id: str
    total_given_score: int
    total_received_score: int
    total_given_count: int
    total_received_count: int
    most_given_emoji: Optional[str]
    most_received_emoji: Optional[str]
    last_activity: Optional[datetime]


class EmojiConfig(BaseModel):
    """Emoji configuration response model."""
    name: str
    score: int
    description: str


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    database_connected: bool
    slack_connected: bool


class ApiStats(BaseModel):
    """API statistics response model."""
    total_users: int
    total_emoji_events: int
    total_score_given: int
    configured_emojis: int


# API Routes
@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    """Root endpoint with basic API information."""
    return {
        "message": "Slack Emoji Tracker API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    # Test database connection
    db_connected = db_manager.test_connection()
    
    # Test Slack connection
    try:
        slack_listener = get_slack_listener()
        slack_connected = slack_listener.test_connection()
    except Exception:
        slack_connected = False
    
    return HealthCheck(
        status="healthy" if db_connected and slack_connected else "unhealthy",
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        slack_connected=slack_connected,
    )


@app.get("/stats", response_model=ApiStats)
async def get_api_stats() -> ApiStats:
    """Get overall API statistics."""
    from sqlalchemy import func
    from src.models.database import EmojiStats, EmojiUsage
    
    session = db_manager.get_session()
    try:
        # Count total users
        total_users = session.query(EmojiStats).count()
        
        # Count total emoji events
        total_events = session.query(EmojiUsage).count()
        
        # Sum total score given
        total_score = session.query(func.sum(EmojiStats.total_given_score)).scalar() or 0
        
        # Count configured emojis
        configured_emojis = len(config.emoji_config.get("emojis", {}))
        
        return ApiStats(
            total_users=total_users,
            total_emoji_events=total_events,
            total_score_given=total_score,
            configured_emojis=configured_emojis,
        )
        
    except Exception as e:
        logger.error(f"Error getting API stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")
    finally:
        db_manager.close_session(session)


@app.get("/users/{slack_id}/stats", response_model=UserStats)
async def get_user_stats(slack_id: str) -> UserStats:
    """Get statistics for a specific user."""
    stats = emoji_tracker.get_user_stats(slack_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserStats(**stats)


@app.get("/leaderboard", response_model=List[UserStats])
async def get_leaderboard(
    limit: int = Query(10, ge=1, le=100, description="Number of users to return"),
    order_by: str = Query(
        "total_received_score",
        regex="^(total_received_score|total_given_score|total_received_count|total_given_count)$",
        description="Field to order by",
    ),
) -> List[UserStats]:
    """Get emoji usage leaderboard."""
    stats = emoji_tracker.get_leaderboard(limit=limit, order_by=order_by)
    return [UserStats(**stat) for stat in stats]


@app.get("/emojis", response_model=List[EmojiConfig])
async def get_emoji_config() -> List[EmojiConfig]:
    """Get configured emoji settings."""
    emojis = config.emoji_config.get("emojis", {})
    
    return [
        EmojiConfig(
            name=name,
            score=emoji_data.get("score", 1),
            description=emoji_data.get("description", ""),
        )
        for name, emoji_data in emojis.items()
    ]


@app.get("/emojis/{emoji_name}", response_model=EmojiConfig)
async def get_emoji_details(emoji_name: str) -> EmojiConfig:
    """Get details for a specific emoji."""
    emojis = config.emoji_config.get("emojis", {})
    
    if emoji_name not in emojis:
        raise HTTPException(status_code=404, detail="Emoji not found in configuration")
    
    emoji_data = emojis[emoji_name]
    return EmojiConfig(
        name=emoji_name,
        score=emoji_data.get("score", 1),
        description=emoji_data.get("description", ""),
    )


@app.get("/users/{slack_id}/history")
async def get_user_history(
    slack_id: str,
    limit: int = Query(50, ge=1, le=500, description="Number of events to return"),
) -> List[Dict]:
    """Get emoji usage history for a specific user."""
    from src.models.database import EmojiUsage
    
    session = db_manager.get_session()
    try:
        # Get user's emoji events
        events = (
            session.query(EmojiUsage)
            .filter(
                (EmojiUsage.giver_slack_id == slack_id) |
                (EmojiUsage.receiver_slack_id == slack_id)
            )
            .order_by(EmojiUsage.created_at.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": event.id,
                "emoji_name": event.emoji_name,
                "emoji_score": event.emoji_score,
                "giver_slack_id": event.giver_slack_id,
                "receiver_slack_id": event.receiver_slack_id,
                "event_type": event.event_type,
                "channel_id": event.channel_id,
                "created_at": event.created_at,
                "context": event.context,
            }
            for event in events
        ]
        
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving user history")
    finally:
        db_manager.close_session(session)


@app.get("/channels/{channel_id}/stats")
async def get_channel_stats(channel_id: str) -> Dict:
    """Get emoji statistics for a specific channel."""
    from sqlalchemy import func
    from src.models.database import EmojiUsage
    
    session = db_manager.get_session()
    try:
        # Get channel statistics
        total_events = (
            session.query(EmojiUsage)
            .filter(EmojiUsage.channel_id == channel_id)
            .count()
        )
        
        total_score = (
            session.query(func.sum(EmojiUsage.emoji_score))
            .filter(EmojiUsage.channel_id == channel_id)
            .scalar() or 0
        )
        
        # Get most popular emojis in this channel
        popular_emojis = (
            session.query(
                EmojiUsage.emoji_name,
                func.count(EmojiUsage.id).label("count"),
                func.sum(EmojiUsage.emoji_score).label("total_score"),
            )
            .filter(EmojiUsage.channel_id == channel_id)
            .group_by(EmojiUsage.emoji_name)
            .order_by(func.count(EmojiUsage.id).desc())
            .limit(10)
            .all()
        )
        
        return {
            "channel_id": channel_id,
            "total_events": total_events,
            "total_score": total_score,
            "popular_emojis": [
                {
                    "emoji_name": emoji.emoji_name,
                    "count": emoji.count,
                    "total_score": emoji.total_score,
                }
                for emoji in popular_emojis
            ],
        }
        
    except Exception as e:
        logger.error(f"Error getting channel stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving channel statistics")
    finally:
        db_manager.close_session(session)


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the application on startup."""
    logger.info("Starting Slack Emoji Tracker API...")
    
    # Test database connection
    if not db_manager.test_connection():
        logger.error("Database connection failed!")
        raise RuntimeError("Database connection failed")
    
    # Create database tables
    try:
        db_manager.create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    logger.info("Slack Emoji Tracker API started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on application shutdown."""
    logger.info("Shutting down Slack Emoji Tracker API...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )