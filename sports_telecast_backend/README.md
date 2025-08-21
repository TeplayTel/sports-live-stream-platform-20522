# Sports Telecast Backend API

A comprehensive FastAPI backend for a sports live streaming platform that provides real-time match data, emoji reactions, and WebSocket support for live updates.

## 🧱 Alembic Version Column Width

Alembic migrations may generate revision identifiers exceeding 32 characters. To prevent failures on applying migrations when the `alembic_version.version_num` column is limited to `VARCHAR(32)`, this repository includes migration `007_expand_alembic_version_length` which widens the column to `VARCHAR(64)`.

No revision IDs are shortened; only the column width is increased to maintain compatibility and best practices.

If you encounter errors related to `alembic_version.version_num` length, ensure you have applied migrations up to at least `007_expand_alembic_version_length`.

## 🏒 Features

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

1. Clone and navigate to the project:
   ```bash
   cd sports-live-stream-platform-20522/sports_telecast_backend
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. Start the server:
   ```bash
   # Preview expects FastAPI to listen on port 3001
   PYTHONPATH=. uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
   ```

6. Access the API:
   - API Documentation: http://localhost:3001/docs
   - Health Check: http://localhost:3001/
   - OpenAPI Spec: http://localhost:3001/openapi.json

## 🛠 Database Setup and Configuration

The backend connects to a PostgreSQL database, using environment variables found in your `.env` file.

If developing in Docker / containerized environments:
- Set `POSTGRES_HOST` to the database service name (e.g. `sports_telecast_db`).
- Example:
  ```
  DATABASE_URL=postgresql://appuser:dbuser123@sports_telecast_db:5001/myapp
  ```
- The default DB user/role is `appuser`. There is no `kavia` user/role, so never use it in your settings.

If developing directly on localhost (no container):
- Use `localhost` for the host fields.
  ```
  DATABASE_URL=postgresql://appuser:dbuser123@localhost:5001/myapp
  ```
- The default database port is `5001` to match the running database container.

Environment Template: see `.env.example` for the correct configuration.

Schema management:
- The app relies on Alembic migrations only.
- Migrations can be run manually using: `alembic upgrade head` (ensure the virtualenv is activated and env vars are set).

## 📚 API Documentation

Refer to the OpenAPI docs available at `/docs` when the server is running.

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

## 🏗 Architecture

See IMPLEMENTATION_SUMMARY.md for implementation details and operational tips.
