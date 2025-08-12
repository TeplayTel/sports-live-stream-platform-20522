# Sports Telecast Backend API Documentation

## Overview

The Sports Telecast Backend API is a comprehensive FastAPI-based REST API that powers a live sports streaming platform. It provides endpoints for user management, match data, real-time emoji reactions, schedules, highlights, and more.

## Base URL
- Development: `http://localhost:8000`
- Production: `https://api.sportstelecast.com`

## Authentication

The API uses JWT (JSON Web Token) based authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## API Categories

### 🔐 Authentication (`/auth`)
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info
- `PUT /auth/me` - Update current user
- `POST /auth/refresh` - Refresh access token

### 👥 Users (`/users`)
- `GET /users` - Get users list with search and filters
- `GET /users/{user_id}` - Get user by ID
- `GET /users/username/{username}` - Get user by username
- `GET /users/search/suggestions` - Get user suggestions for autocomplete
- `GET /users/stats/overview` - Get user statistics
- `PUT /users/{user_id}/activate` - Activate user (admin only)
- `PUT /users/{user_id}/deactivate` - Deactivate user (admin/self)

### 👤 User Profiles (`/profiles`)
- `POST /profiles/` - Create user profile
- `GET /profiles/me` - Get current user's profile
- `PUT /profiles/me` - Update current user's profile
- `GET /profiles/{profile_id}` - Get profile by ID
- `GET /profiles/` - Search user profiles
- `DELETE /profiles/me` - Delete current user's profile

### ⚽ Matches (`/matches`)
- `GET /matches` - Get matches with filtering
- `GET /matches/{match_id}` - Get match details
- `GET /matches/live` - Get currently live matches
- `GET /matches/upcoming` - Get upcoming matches
- `GET /matches/more` - Get additional matches
- `GET /events` - Get sports events
- `GET /events/{event_id}` - Get event details

### 📅 Schedules (`/schedules`)
- `GET /schedules/daily/{date}` - Get daily schedule
- `GET /schedules/weekly` - Get weekly schedule
- `GET /schedules/upcoming` - Get upcoming schedules
- `GET /schedules/live` - Get live matches schedule
- `GET /schedules/` - Get schedules list
- `POST /schedules/` - Create schedule
- `PUT /schedules/{schedule_id}` - Update schedule
- `DELETE /schedules/{schedule_id}` - Delete schedule

### 🎬 Highlights (`/highlights`)
- `GET /highlights` - Get highlights with filtering
- `GET /highlights/{highlight_id}` - Get highlight details
- `GET /highlights/featured` - Get featured highlights

### 😊 Emoji Reactions (`/fan-engagement/emoji/v1`)
- `GET /fan-engagement/emoji/v1/listEmojis` - List available emojis
- `POST /fan-engagement/emoji/v1/userEmojiReaction` - Submit emoji reaction
- `GET /fan-engagement/emoji/v1/reactions/{event_id}` - Get reaction summary

### 🔗 WebSocket (`/ws`)
- `WS /ws/{event_id}` - WebSocket connection for real-time updates

### 📊 API Monitoring (`/api-logs`)
- `GET /api-logs/calls` - Get recent API calls
- `GET /api-logs/stats` - Get API statistics
- `GET /api-logs/endpoints` - Get available endpoints
- `DELETE /api-logs/clear` - Clear logs

### 🏥 Health (`/`)
- `GET /` - Health check
- `GET /health/database` - Database health check

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response
```json
{
  "error": "error_type",
  "message": "Human readable error message",
  "details": { ... },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Authentication Flow

1. **Register**: `POST /auth/register` with user details
2. **Login**: `POST /auth/login` with email/password
3. **Use Token**: Include JWT token in Authorization header for protected endpoints
4. **Refresh**: `POST /auth/refresh` when token expires

## Real-time Features

### WebSocket Connection
Connect to `/ws/{event_id}?token=your_jwt_token` for:
- Live emoji reaction updates
- Real-time match score changes
- Live match event updates

### Emoji Reactions
1. Get available emojis: `GET /fan-engagement/emoji/v1/listEmojis`
2. Submit reaction: `POST /fan-engagement/emoji/v1/userEmojiReaction`
   - userId can be provided via:
     - Header: `X-User-Id: <USER_ID>` (recommended)
     - Query param: `?user_id=<USER_ID>` or `?userId=<USER_ID>`
     - Request body: `{"userId": "<USER_ID>"}` or `{"user_id": "<USER_ID>"}`
3. Get summary: `GET /fan-engagement/emoji/v1/reactions/{event_id}`

## Pagination

List endpoints support pagination with query parameters:
- `limit`: Number of items to return (default: 20, max: 100)
- `offset`: Number of items to skip (default: 0)
- `page`: Page number (alternative to offset)

Example: `GET /users?limit=10&offset=20`

## Filtering and Search

Many endpoints support filtering:
- **Users**: Search by username/email, filter by role/status
- **Matches**: Filter by sport type, status, date range
- **Profiles**: Search by display name, filter by location/sports
- **Schedules**: Filter by date range, sport type

## Rate Limiting

- Unauthenticated: 100 requests/minute
- Authenticated: 1000 requests/minute
- WebSocket connections: 10 concurrent per user

## Error Codes

- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (data validation errors)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

## Interactive Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

## Testing

Use the provided test script to validate all endpoints:
```bash
python test_comprehensive_api.py --url http://localhost:8000
```

## Support

For API support and questions, contact: support@sportstelecast.com
