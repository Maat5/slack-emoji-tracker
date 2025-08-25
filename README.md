# Slack Emoji Tracker

A comprehensive Python application that tracks Slack emoji usage with scoring capabilities. Monitor emoji reactions and messages across your Slack workspace and generate statistics and leaderboards.

## Features

- **Real-time Emoji Tracking**: Listen to Slack events for emoji reactions and messages
- **Configurable Scoring System**: Define custom scores for different emojis using JSON configuration
- **User Statistics**: Track who gives and receives emojis with accumulative scores
- **REST API**: Query usage statistics and leaderboards via FastAPI endpoints
- **PostgreSQL Storage**: Robust database storage with SQLAlchemy and Alembic migrations
- **Slack Integration**: Full Slack SDK integration with Socket Mode for real-time events

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, SQLAlchemy
- **Database**: PostgreSQL with Alembic migrations
- **Slack Integration**: Slack SDK for Python (Socket Mode)
- **Configuration**: JSON-based configuration (no YAML dependency)
- **Dependency Management**: Poetry
- **Development**: Docker Compose for PostgreSQL

## Quick Start

### 1. Prerequisites

- Python 3.9+
- Poetry
- Docker and Docker Compose (for database)
- Slack workspace with admin access

### 2. Clone and Setup

```bash
git clone <repository-url>
cd slack-emoji-tracker

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env
```

### 3. Configure Environment

Edit `.env` file with your configuration:

```env
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/slack_emoji_tracker

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

### 4. Start Database

```bash
# Start PostgreSQL with Docker Compose
docker-compose up -d postgres

# Wait for database to be ready
docker-compose logs postgres
```

### 5. Run Database Migrations

```bash
# Initialize Alembic (first time only)
poetry run alembic revision --autogenerate -m "Initial migration"

# Run migrations
poetry run alembic upgrade head
```

### 6. Start the Application

```bash
# Start the REST API
poetry run python -m src.api.main

# In another terminal, start the Slack listener
poetry run python -c "
from src.slack.event_listener import slack_listener
try:
    slack_listener.start()
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    slack_listener.stop()
"
```

## Configuration

### Emoji Configuration

Configure emoji scores and tracking in `config/emoji_config.json`:

```json
{
  "emojis": {
    "thumbsup": {
      "name": "thumbsup",
      "score": 1,
      "description": "Positive reaction"
    },
    "heart": {
      "name": "heart",
      "score": 2,
      "description": "Love and appreciation"
    },
    "fire": {
      "name": "fire",
      "score": 3,
      "description": "Excellent work"
    },
    "rocket": {
      "name": "rocket",
      "score": 5,
      "description": "Exceptional performance"
    },
    "trophy": {
      "name": "trophy",
      "score": 10,
      "description": "Major achievement"
    }
  },
  "settings": {
    "default_score": 1,
    "track_all_emojis": false,
    "case_sensitive": false
  }
}
```

#### Configuration Options

- **emojis**: Dictionary of emoji configurations
  - `name`: Emoji name (without colons)
  - `score`: Point value for this emoji
  - `description`: Human-readable description

- **settings**:
  - `default_score`: Score for unconfigured emojis (when `track_all_emojis` is true)
  - `track_all_emojis`: Whether to track all emojis or only configured ones
  - `case_sensitive`: Whether emoji names are case-sensitive

## Slack App Setup

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Emoji Tracker") and select your workspace

### 2. Configure Bot Permissions

In **OAuth & Permissions**, add these Bot Token Scopes:

```
channels:history
channels:read
chat:write
emoji:read
reactions:read
users:read
users:read.email
```

### 3. Enable Socket Mode

1. Go to **Socket Mode** and enable it
2. Generate an App-Level Token with `connections:write` scope
3. Copy the token (starts with `xapp-`)

### 4. Enable Events

1. Go to **Event Subscriptions** and enable events
2. Subscribe to these Bot Events:
   ```
   message.channels
   reaction_added
   reaction_removed
   app_mention
   ```

### 5. Install App

1. Go to **Install App** and install to your workspace
2. Copy the Bot User OAuth Token (starts with `xoxb-`)
3. Copy the Signing Secret from **Basic Information**

## API Endpoints

The REST API provides several endpoints for querying emoji statistics:

### Health & Status

- `GET /` - API information
- `GET /health` - Health check with database and Slack status
- `GET /stats` - Overall API statistics

### User Statistics

- `GET /users/{slack_id}/stats` - Get statistics for a specific user
- `GET /users/{slack_id}/history` - Get emoji usage history for a user

### Leaderboards

- `GET /leaderboard` - Get emoji usage leaderboard
  - Query parameters:
    - `limit` (1-100): Number of users to return
    - `order_by`: Field to sort by (`total_received_score`, `total_given_score`, etc.)

### Configuration

- `GET /emojis` - Get all configured emojis
- `GET /emojis/{emoji_name}` - Get details for a specific emoji

### Channel Statistics

- `GET /channels/{channel_id}/stats` - Get emoji statistics for a channel

### Example API Usage

```bash
# Get top 10 users by received score
curl "http://localhost:8000/leaderboard?limit=10&order_by=total_received_score"

# Get user statistics
curl "http://localhost:8000/users/U1234567890/stats"

# Get configured emojis
curl "http://localhost:8000/emojis"

# Get API health
curl "http://localhost:8000/health"
```

## Database Schema

The application uses PostgreSQL with the following main tables:

- **users**: Slack user information
- **emoji_usage**: Individual emoji events
- **emoji_stats**: Aggregated user statistics
- **channels**: Slack channel information

## Development

### Running Tests

```bash
# Run tests (when implemented)
poetry run pytest

# Run with coverage
poetry run pytest --cov=src
```

### Code Quality

```bash
# Format code
poetry run black src/

# Sort imports
poetry run isort src/

# Lint code
poetry run flake8 src/

# Type checking
poetry run mypy src/
```

### Database Management

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use secure values for all tokens and secrets
2. **Database**: Use a production PostgreSQL instance
3. **CORS**: Configure appropriate CORS origins in the API
4. **Logging**: Set appropriate log levels
5. **Monitoring**: Add health checks and monitoring

### Docker Deployment

You can create a production Docker setup:

```dockerfile
# Dockerfile example
FROM python:3.9-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "-m", "src.api.main"]
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env file
   - Verify database exists

2. **Slack Connection Error**
   - Verify Bot Token and App Token are correct
   - Check Slack app permissions
   - Ensure Socket Mode is enabled

3. **Missing Emoji Events**
   - Verify bot is added to channels
   - Check event subscriptions in Slack app
   - Review application logs

### Logs

Application logs include:
- Slack event processing
- Database operations
- API requests
- Error details

Set `LOG_LEVEL=DEBUG` for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run code quality checks
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Open an issue with detailed information