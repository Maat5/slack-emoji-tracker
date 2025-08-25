# Slack Emoji Tracker 🎯

A comprehensive Slack emoji tracking system that monitors emoji usage across Slack workspaces with configurable scoring capabilities. The system provides real-time tracking, statistics generation, and a REST API for querying usage data.

## 🌟 Key Features

### 🏗️ Architecture & Technology Stack
- **Poetry** for dependency management (no PyYAML dependency)
- **FastAPI** for the REST API with automatic OpenAPI documentation
- **SQLAlchemy** with PostgreSQL for robust data storage
- **Alembic** for database migrations
- **Slack SDK** with Socket Mode for real-time event handling
- **JSON-based configuration** for emoji scoring

### 📊 Slack Integration
The system listens to Slack events in real-time:
- **Reaction tracking**: Monitors when users add emoji reactions to messages
- **Message emoji tracking**: Detects emojis used within message text
- **User synchronization**: Automatically creates/updates user profiles with Slack data
- **Channel tracking**: Records emoji usage per channel for analytics

### 🎯 Scoring System
Configurable emoji scoring through `config/emoji_config.json`:
```json
{
  "emojis": {
    "thumbsup": {"score": 1, "description": "Positive reaction"},
    "heart": {"score": 2, "description": "Love and appreciation"},
    "fire": {"score": 3, "description": "Excellent work"},
    "rocket": {"score": 5, "description": "Exceptional performance"},
    "trophy": {"score": 10, "description": "Major achievement"}
  },
  "settings": {
    "default_score": 1,
    "track_all_emojis": false,
    "case_sensitive": false
  }
}
```

### 💾 Database Schema
Four main tables for comprehensive tracking:
- **users**: Slack user information (ID, email, display name)
- **emoji_usage**: Individual emoji events with full context
- **emoji_stats**: Aggregated statistics for fast queries
- **channels**: Slack channel metadata

### 🌐 REST API Endpoints

#### Health & System
- `GET /health` - System health with database/Slack connection status
- `GET /stats/global` - Global emoji usage statistics

#### User Management
- `GET /users` - List all users with pagination
- `GET /users/{slack_id}/stats` - Individual user statistics
- `GET /users/{slack_id}/history` - User's emoji usage history

#### Leaderboards & Analytics
- `GET /leaderboard` - Sortable leaderboards (by received/given score/count)
- `GET /channels` - List all channels
- `GET /channels/{channel_id}/stats` - Channel-specific analytics

#### Configuration
- `GET /emojis` - View configured emoji settings

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL
- Poetry
- Slack workspace with bot permissions

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd slack-emoji-tracker
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set up PostgreSQL**
   ```bash
   # Using Docker Compose (recommended)
   docker-compose up -d postgres
   
   # Or install PostgreSQL manually and create database
   createdb slack_emoji_tracker
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Slack tokens and database URL
   ```

5. **Initialize database**
   ```bash
   poetry run python main.py setup-db
   ```

### Configuration

#### Environment Variables (.env)
```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Database Configuration  
DATABASE_URL=postgresql://postgres:password@localhost:5432/slack_emoji_tracker

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### Slack App Setup
1. Create a new Slack app at https://api.slack.com/apps
2. Enable Socket Mode and generate App Token
3. Add Bot Token Scopes:
   - `reactions:read`
   - `channels:read`
   - `groups:read`
   - `users:read`
   - `users:read.email`
4. Subscribe to Bot Events:
   - `reaction_added`
   - `message.channels`
   - `message.groups`
   - `user_change`
   - `channel_created`
   - `channel_rename`
5. Install the app to your workspace

## 🎮 Usage

### Running Components

The system provides multiple run modes through the main script:

```bash
# Test all connections
poetry run python main.py test

# Start REST API server
poetry run python main.py api

# Start Slack event listener
poetry run python main.py slack

# Initialize/setup database
poetry run python main.py setup-db
```

### Development Workflow

1. **Start PostgreSQL**
   ```bash
   docker-compose up -d postgres
   ```

2. **Initialize database** (first time only)
   ```bash
   poetry run python main.py setup-db
   ```

3. **Test connections**
   ```bash
   poetry run python main.py test
   ```

4. **Start both services** (in separate terminals)
   ```bash
   # Terminal 1: API Server
   poetry run python main.py api
   
   # Terminal 2: Slack Listener
   poetry run python main.py slack
   ```

### API Documentation

Once the API is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Database Management

Access the database through Adminer (when using Docker Compose):
- **URL**: http://localhost:8080
- **Server**: postgres
- **Username**: postgres
- **Password**: password
- **Database**: slack_emoji_tracker

## 📚 API Examples

### Get User Statistics
```bash
curl http://localhost:8000/users/U1234567890/stats
```

### Get Leaderboard
```bash
# By received score (default)
curl http://localhost:8000/leaderboard

# By given count
curl http://localhost:8000/leaderboard?sort_by=given_count&limit=10
```

### Get Channel Statistics
```bash
curl http://localhost:8000/channels/C1234567890/stats
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 🔧 Development

### Code Structure
```
slack-emoji-tracker/
├── src/slack_emoji_tracker/          # Main Python package
│   ├── __init__.py                   # Package initialization
│   ├── config.py                     # Configuration management
│   ├── models.py                     # SQLAlchemy database models
│   ├── database.py                   # Database connection utilities
│   ├── service.py                    # Core business logic
│   ├── slack_service.py              # Slack integration
│   ├── api.py                        # FastAPI application
│   └── schemas.py                    # Pydantic response models
├── config/
│   └── emoji_config.json             # Emoji scoring configuration
├── migrations/                       # Alembic database migrations
├── main.py                          # Multi-mode entry point
├── pyproject.toml                   # Poetry configuration
├── docker-compose.yml               # PostgreSQL setup
└── README.md                        # This file
```

### Adding New Emojis

Edit `config/emoji_config.json` to add or modify emoji scores:

```json
{
  "emojis": {
    "new_emoji": {"score": 5, "description": "Description here"}
  }
}
```

The system will automatically use the new configuration without restart.

### Database Migrations

```bash
# Generate new migration (when models change)
poetry run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
poetry run alembic upgrade head

# View migration history
poetry run alembic history
```

## 🧪 Testing

### Test All Connections
```bash
poetry run python main.py test
```

This will test:
- Database connectivity
- Emoji configuration loading
- Slack API connectivity
- Configuration validation

### Manual Testing

1. **Start both services**
2. **Add emoji reactions** in your Slack workspace
3. **Check the API** for updated statistics
4. **View real-time logs** for tracking activity

## 🚨 Troubleshooting

### Common Issues

**Database Connection Errors**
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- Verify database exists and permissions

**Slack Connection Errors**
- Verify SLACK_BOT_TOKEN and SLACK_APP_TOKEN
- Check bot permissions and scopes
- Ensure Socket Mode is enabled

**No Emoji Tracking**
- Check emoji configuration in config/emoji_config.json
- Verify bot has access to channels
- Check logs for tracking events

### Logs

All components provide detailed logging. Set LOG_LEVEL in .env:
- `DEBUG`: Verbose logging including all events
- `INFO`: Standard operational logging
- `WARNING`: Only warnings and errors
- `ERROR`: Only errors

## 📈 Monitoring

### Health Endpoint

The `/health` endpoint provides system status:

```json
{
  "status": "healthy",
  "database": true,
  "slack": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

Status values:
- `healthy`: All systems operational
- `degraded`: Some systems have issues
- `unhealthy`: Critical systems down

### Performance

The system uses:
- Connection pooling for database efficiency
- Aggregated statistics tables for fast queries
- Indexed columns for optimal query performance
- Async processing for Slack events

## 🔒 Security

- Environment variables for sensitive configuration
- No hardcoded secrets in source code
- Database connection with proper credentials
- API rate limiting (configure as needed)

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Create an issue with reproduction steps