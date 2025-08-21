# Sports Telecast Backend API

A comprehensive FastAPI backend for a sports live streaming platform that provides real-time match data, emoji reactions, and WebSocket support for live updates.

## 🧱 Project Overview

- FastAPI backend with async SQLAlchemy
- PostgreSQL with Alembic migrations
- JWT authentication
- Real-time WebSocket updates
- Users, Profiles, Emojis, Matches, Highlights data models

## ⚙️ Alembic and PYTHONPATH (Importing `src`)

To run Alembic migrations, ensure the `src` package is importable. Always run Alembic from the backend root and set `PYTHONPATH=.` (the backend root):

- Unix/macOS:
  PYTHONPATH=. alembic upgrade head

- Windows (PowerShell):
  $env:PYTHONPATH="."; alembic upgrade head

The Alembic `env.py` also prepends the backend root to `sys.path` automatically, so running from this directory typically just works. If you still see `ModuleNotFoundError: No module named 'src'`, verify you are in:
sports-live-stream-platform-20522/sports_telecast_backend

## 🧾 Alembic Version Column Width

Alembic migrations may generate revision identifiers exceeding 32 characters. To prevent failures when the `alembic_version.version_num` column is `VARCHAR(32)`, Alembic env includes logic to widen to `VARCHAR(64)` automatically and applies a temporary in-memory truncation patch only when needed.

## 🏁 Quick Start

### Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### Installation

1. Navigate to the project:
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

5. Initialize/upgrade database schema to latest (creates tables, including users):
   ```bash
   # Option A: helper script (recommended)
   python init_db.py
   # Option B: Alembic CLI (ensure env vars are set)
   PYTHONPATH=. alembic upgrade head
   ```

6. Start the server:
   ```bash
   # FastAPI listens on port 3001 for the preview
   PYTHONPATH=. uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
   ```

7. Access the API:
   - API Documentation: http://localhost:3001/docs
   - Health Check: http://localhost:3001/
   - OpenAPI Spec: http://localhost:3001/openapi.json

## 🛠️ Database Setup and Configuration

The backend connects to a PostgreSQL database, using environment variables found in your `.env` file.

If developing in Docker / containerized environments:
- Set `POSTGRES_HOST` to the database service name (e.g. `sports_telecast_db`).
- Example:
  ```
  DATABASE_URL=postgresql://appuser:dbuser123@sports_telecast_db:5001/myapp
  ```
- The default DB user/role is `appuser`.

If developing directly on localhost (no container):
- Use `localhost` for the host fields.
  ```
  DATABASE_URL=postgresql://appuser:dbuser123@localhost:5001/myapp
  ```
- The default database port is `5001` to match the running database container.

Environment Template: see `.env.example` for the correct configuration.

Schema management:
- The app relies on Alembic migrations only.
- Migrations can be run manually using: `PYTHONPATH=. alembic upgrade head` (ensure the virtualenv is activated and env vars are set).
- The helper `python init_db.py` runs Alembic using the configured URL with async engine and an advisory lock.

### Ensuring the "users" table exists

This project includes an idempotent migration `007_users_table_jwt_prep` that:
- Ensures the enum `userroleenum` exists.
- Creates the `users` table if missing (UUID PK).
- Adds any missing columns.
- Ensures a primary key on `user_id`.
- Creates unique indexes on `email` and `username` if no duplicates exist.

To apply all migrations against your configured database, run one of:
- Preferred:
  ```bash
  python init_db.py
  ```
- Alembic CLI:
  ```bash
  PYTHONPATH=. alembic upgrade head
  ```

If you get:
- asyncpg.exceptions.UndefinedTableError: relation "users" does not exist (e.g., when calling `/auth/register` or `/auth/login`):

Steps to resolve:
1) Verify your `.env` points to the exact same DB the server uses (DATABASE_URL or POSTGRES_*).  
2) Apply migrations:
   ```bash
   python init_db.py
   # or
   PYTHONPATH=. alembic upgrade head
   ```
3) If the DB has a partial/old state (development only), you may run:
   ```bash
   python manage_db.py alembic-upgrade head
   # If necessary for dev cleanup (affects migration tracking):
   python manage_db.py alembic-reset
   PYTHONPATH=. alembic upgrade head
   ```

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

## 🎯 Architecture

See IMPLEMENTATION_SUMMARY.md for implementation details and operational tips.
