# Sports Telecast Backend API

A comprehensive FastAPI backend for a sports live streaming platform that provides real-time match data, emoji reactions, and WebSocket support for live updates.

## 🏟️ Features

- **Live Match Data**: Real-time scores, events, and statistics
- **Event Schedules**: Upcoming matches and tournament information
- **Match Highlights**: Video highlights and key moments
- **Emoji Reactions**: Interactive emoji reactions during live events with real-time updates
- **JWT Authentication**: Secure token-based authentication
- **WebSocket Support**: Real-time connections for live updates
- **User Management**: User profiles and preferences
- **RESTful API**: Well-documented REST endpoints

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd sports-live-stream-platform-20522/sports_telecast_backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Start the server**:
   ```bash
   PYTHONPATH=. uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/
   - OpenAPI Spec: http://localhost:8000/openapi.json

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | User login | No |
| GET | `/auth/me` | Get current user profile | Yes |
| PUT | `/auth/me` | Update user profile | Yes |
| POST | `/auth/refresh` | Refresh access token | Yes |

### Match & Event Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/matches/` | Get paginated matches list | Optional |
| GET | `/matches/live` | Get currently live matches | Optional |
| GET | `/matches/{match_id}` | Get match details | Optional |
| GET | `/matches/{match_id}/highlights` | Get match highlights | Optional |
| GET | `/matches/schedule/upcoming` | Get upcoming matches | Optional |
| GET | `/matches/events/` | Get events/tournaments list | Optional |
| GET | `/matches/events/{event_id}` | Get event details | Optional |
| GET | `/matches/events/{event_id}/matches` | Get event matches | Optional |

### Fan Engagement - Emoji Reactions

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/fan-engagement/emoji/v1/listEmojis` | List available emojis | Yes |
| POST | `/fan-engagement/emoji/v1/userEmojiReaction` | Submit emoji reaction | Yes |
| GET | `/fan-engagement/emoji/v1/reactions/{event_id}` | Get reaction summary | Optional |

### Highlights Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/highlights/` | Get highlights list | Optional |
| GET | `/highlights/{highlight_id}` | Get highlight details | Optional |
| GET | `/highlights/featured/latest` | Get featured highlights | Optional |

### Real-time WebSocket

| Endpoint | Description | Auth Required |
|----------|-------------|---------------|
| `ws://localhost:8000/ws/{event_id}?token={jwt_token}` | WebSocket connection for real-time updates | Optional |
| GET `/ws/stats` | WebSocket connection statistics | No |

## 🎯 Emoji Reactions API

The emoji reactions feature follows the specified API contract:

### List Emojis
```bash
curl -X GET "http://localhost:8000/fan-engagement/emoji/v1/listEmojis?pageNo=1&pageSize=10" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "status": "SUCCESS",
  "emojis": [
    {
      "emojiId": "EMJ103",
      "emojiType": "clap",
      "imageUrl": "https://cdn.mydomain.com/emojis/clap.png"
    }
  ]
}
```

### Submit Reaction
```bash
curl -X POST "http://localhost:8000/fan-engagement/emoji/v1/userEmojiReaction" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "userId": "USR456",
    "eventId": "EVT123", 
    "emojiId": "EMJ001",
    "createdAt": "2025-07-29T11:35:24Z"
  }'
```

## 🔌 WebSocket Real-time Updates

Connect to WebSocket for live emoji reaction updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/EVT123?token=your_jwt_token');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'emoji_reaction_update') {
        // Handle emoji reaction update
        console.log('New reaction:', data.data);
    }
};

// Send ping
ws.send(JSON.stringify({
    "type": "ping",
    "timestamp": new Date().toISOString()
}));
```

## 🧪 Testing

Run the comprehensive API test suite:

```bash
# Make sure the server is running first
python test_api.py
```

Test WebSocket connections:

```bash
python test_websocket.py
```

## 🏗️ Architecture

### Project Structure
```
src/
├── api/           # API endpoints and routes
├── auth/          # Authentication and JWT handling
├── database/      # Database connection and models
├── models/        # Pydantic data models
└── websocket/     # WebSocket connection management
```

### Key Components

1. **FastAPI Application**: Main API server with automatic documentation
2. **JWT Authentication**: Secure token-based auth with bcrypt password hashing
3. **WebSocket Manager**: Real-time connection management for live updates
4. **Mock Database**: In-memory data store (replace with PostgreSQL in production)
5. **Pydantic Models**: Type-safe data validation and serialization

### Sample Data

The backend includes sample data for testing:
- **Teams**: Arsenal, Chelsea, Manchester United, Liverpool
- **Matches**: Live, scheduled, and finished matches
- **Emojis**: 5 reaction types (clap, fire, heart, thumbs_up, goal)
- **Events**: Premier League 2024-25 season
- **Highlights**: Video highlights for completed matches

## 🔧 Configuration

Environment variables (see `.env.example`):

**Database URL for PostgreSQL — Required**

You must set either `POSTGRES_URL` (recommended, aligns with Docker and most cloud envs) **or** `DATABASE_URL` (if you're using hosting providers/services that set this by default).

- If **both** variables are set, the backend will use `DATABASE_URL` by default.
- If **neither** is set when the app starts, the backend will fail to start and throw an error:  
  _"DATABASE_URL or POSTGRES_URL must be set as an environment variable for DB connection..."_

Example `.env`:
```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database connection string
POSTGRES_URL=postgresql+psycopg2://user:password@localhost:5432/sports_telecast
# DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/sports_telecast  # Optional, if used with certain cloud platforms

POSTGRES_USER=sports_user
POSTGRES_PASSWORD=sports_password
POSTGRES_DB=sports_telecast_db
POSTGRES_PORT=5432

# External Services
CDN_BASE_URL=https://cdn.mydomain.com
STREAM_BASE_URL=https://stream.mydomain.com
```

## 🚀 Production Deployment

For production deployment:

1. **Replace Mock Database**: Integrate with PostgreSQL using SQLAlchemy
2. **Environment Variables**: Set secure JWT secrets and database credentials
3. **CORS Configuration**: Restrict origins to your frontend domains
4. **Rate Limiting**: Implement API rate limiting
5. **Logging**: Configure structured logging
6. **Health Checks**: Set up monitoring and health check endpoints
7. **Docker**: Containerize the application

## 📖 API Examples

### Register and Get Matches

```bash
# Register user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "sportsfan",
    "password": "securepass123",
    "full_name": "Sports Fan"
  }'

# Get live matches
curl -X GET "http://localhost:8000/matches/live"

# Get match details
curl -X GET "http://localhost:8000/matches/MATCH001"
```

### Emoji Reactions Flow

```bash
# 1. Get available emojis
curl -X GET "http://localhost:8000/fan-engagement/emoji/v1/listEmojis" \
  -H "Authorization: Bearer $TOKEN"

# 2. Submit reaction
curl -X POST "http://localhost:8000/fan-engagement/emoji/v1/userEmojiReaction" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"userId": "USR123", "eventId": "MATCH001", "emojiId": "EMJ103"}'

# 3. Get reaction summary
curl -X GET "http://localhost:8000/fan-engagement/emoji/v1/reactions/MATCH001"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_api.py`
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- 📧 Email: support@sportstelecast.com
- 📚 Documentation: http://localhost:8000/docs
- 🐛 Issues: Create an issue in the repository

---

**Happy coding! 🏟️⚽**
