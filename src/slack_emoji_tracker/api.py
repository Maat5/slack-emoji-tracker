"""FastAPI application for the Slack Emoji Tracker REST API."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import config
from .database import check_database_connection, get_db
from .schemas import (
    ChannelStats,
    EmojiConfigResponse,
    ErrorResponse,
    HealthStatus,
    LeaderboardEntry,
    LeaderboardResponse,
    UserHistoryResponse,
    UserStats,
)
from .service import EmojiService
from .slack_service import SlackService

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Slack Emoji Tracker API",
    description="A comprehensive REST API for tracking and analyzing emoji usage in Slack workspaces",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Slack service instance (optional, for health checks)
slack_service: Optional[SlackService] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global slack_service
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info("Starting Slack Emoji Tracker API...")
    
    # Optionally initialize Slack service for health checks
    try:
        if config.slack_bot_token and config.slack_app_token:
            slack_service = SlackService()
    except Exception as e:
        logger.warning(f"Could not initialize Slack service: {e}")


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Get system health status including database and Slack connection status.
    """
    # Check database connection
    db_healthy = check_database_connection()
    
    # Check Slack connection if available
    slack_healthy = None
    if slack_service:
        try:
            slack_healthy = await slack_service.test_connection()
        except Exception as e:
            logger.error(f"Slack health check failed: {e}")
            slack_healthy = False
    
    status = "healthy" if db_healthy else "unhealthy"
    if slack_healthy is False:
        status = "degraded"
    
    return HealthStatus(
        status=status,
        database=db_healthy,
        slack=slack_healthy,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/users/{slack_id}/stats", response_model=UserStats)
async def get_user_stats(slack_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive statistics for a specific user including totals and top emojis given/received.
    """
    emoji_service = EmojiService(db, slack_service.web_client if slack_service else None)
    stats = emoji_service.get_user_stats(slack_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="User not found")
    
    return stats


@app.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    sort_by: str = Query(
        "received_score",
        description="Sort field: received_score, received_count, given_score, given_count",
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of entries to return"),
    db: Session = Depends(get_db),
):
    """
    Get leaderboard data sorted by various metrics (received/given score/count).
    """
    emoji_service = EmojiService(db, slack_service.web_client if slack_service else None)
    entries = emoji_service.get_leaderboard(sort_by=sort_by, limit=limit)
    
    return LeaderboardResponse(
        entries=entries,
        sort_by=sort_by,
        total_users=len(entries),
    )


@app.get("/users/{slack_id}/history", response_model=UserHistoryResponse)
async def get_user_history(
    slack_id: str,
    limit: int = Query(100, ge=1, le=500, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    db: Session = Depends(get_db),
):
    """
    Get recent emoji usage history for a specific user with pagination.
    """
    emoji_service = EmojiService(db, slack_service.web_client if slack_service else None)
    history = emoji_service.get_user_history(slack_id, limit=limit, offset=offset)
    
    if not history:
        raise HTTPException(status_code=404, detail="User not found")
    
    return history


@app.get("/emojis", response_model=EmojiConfigResponse)
async def get_emoji_config():
    """
    Get the current emoji configuration including scores and settings.
    """
    return EmojiConfigResponse(
        emojis={
            name: {"score": emoji["score"], "description": emoji["description"]}
            for name, emoji in config.emoji_config["emojis"].items()
        },
        settings=config.emoji_config["settings"],
    )


@app.get("/channels/{channel_id}/stats", response_model=ChannelStats)
async def get_channel_stats(channel_id: str, db: Session = Depends(get_db)):
    """
    Get emoji statistics for a specific channel including totals, top emojis, and top users.
    """
    emoji_service = EmojiService(db, slack_service.web_client if slack_service else None)
    stats = emoji_service.get_channel_stats(channel_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return stats


@app.get("/users", response_model=List[dict])
async def list_users(
    limit: int = Query(100, ge=1, le=500, description="Number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    db: Session = Depends(get_db),
):
    """
    Get a list of all users in the system with basic information.
    """
    from .models import User
    
    users = (
        db.query(User)
        .filter(User.is_active == True)
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "slack_id": user.slack_id,
            "display_name": user.display_name,
            "real_name": user.real_name,
            "email": user.email,
            "is_bot": user.is_bot,
        }
        for user in users
    ]


@app.get("/channels", response_model=List[dict])
async def list_channels(
    limit: int = Query(100, ge=1, le=500, description="Number of channels to return"),
    offset: int = Query(0, ge=0, description="Number of channels to skip"),
    db: Session = Depends(get_db),
):
    """
    Get a list of all channels in the system with basic information.
    """
    from .models import Channel
    
    channels = (
        db.query(Channel)
        .filter(Channel.is_archived == False)
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "slack_id": channel.slack_id,
            "name": channel.name,
            "is_private": channel.is_private,
            "is_archived": channel.is_archived,
        }
        for channel in channels
    ]


@app.get("/stats/global", response_model=dict)
async def get_global_stats(db: Session = Depends(get_db)):
    """
    Get global statistics about emoji usage across the entire workspace.
    """
    from sqlalchemy import func
    from .models import EmojiUsage, User, Channel
    
    # Total usage statistics
    total_usage = (
        db.query(
            func.count(EmojiUsage.id).label("total_usage"),
            func.sum(EmojiUsage.emoji_score).label("total_score"),
            func.count(func.distinct(EmojiUsage.emoji_name)).label("unique_emojis"),
        )
        .first()
    )
    
    # User and channel counts
    user_count = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    channel_count = db.query(func.count(Channel.id)).filter(Channel.is_archived == False).scalar()
    
    # Top emojis globally
    top_emojis = (
        db.query(
            EmojiUsage.emoji_name,
            func.count(EmojiUsage.id).label("count"),
            func.sum(EmojiUsage.emoji_score).label("score"),
        )
        .group_by(EmojiUsage.emoji_name)
        .order_by(func.sum(EmojiUsage.emoji_score).desc())
        .limit(10)
        .all()
    )
    
    return {
        "totals": {
            "total_usage": total_usage.total_usage or 0,
            "total_score": total_usage.total_score or 0,
            "unique_emojis": total_usage.unique_emojis or 0,
            "active_users": user_count or 0,
            "active_channels": channel_count or 0,
        },
        "top_emojis": [
            {
                "emoji": emoji.emoji_name,
                "count": emoji.count,
                "score": emoji.score,
            }
            for emoji in top_emojis
        ],
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(exc.detail)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle internal server errors."""
    from fastapi.responses import JSONResponse
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "slack_emoji_tracker.api:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.environment == "development",
    )