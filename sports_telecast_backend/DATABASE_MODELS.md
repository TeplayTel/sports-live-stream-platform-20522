# Database Models Documentation

## Overview

The Sports Telecast Backend uses SQLAlchemy ORM models that perfectly mirror the Pydantic models defined in the OpenAPI specification. This ensures consistency between the database schema and the API contract.

## Model Structure

### Core Models

#### UserDB
- **Purpose**: Stores user account information and preferences
- **Key Fields**: `user_id`, `email`, `username`, `password_hash`, `role`, `preferences`
- **Relationships**: One-to-many with `UserEmojiReactionDB`
- **Pydantic Mirror**: `User`, `UserResponse`, `UserCreate`, `UserUpdate`

#### TeamDB
- **Purpose**: Stores sports team information
- **Key Fields**: `team_id`, `name`, `short_name`, `logo_url`, `colors`
- **Relationships**: One-to-many with `MatchDB` (as home and away teams)
- **Pydantic Mirror**: `Team`

#### EventDB
- **Purpose**: Stores sports events/tournaments information
- **Key Fields**: `event_id`, `name`, `sport_type`, `start_date`, `end_date`, `is_featured`
- **Relationships**: One-to-many with `MatchDB`
- **Pydantic Mirror**: `Event`

#### MatchDB
- **Purpose**: Stores individual match information
- **Key Fields**: `match_id`, `event_id`, `home_team_id`, `away_team_id`, `status`, `home_score`, `away_score`
- **Relationships**: 
  - Many-to-one with `EventDB`
  - Many-to-one with `TeamDB` (home and away)
  - One-to-many with `MatchEventDB` and `HighlightDB`
- **Pydantic Mirror**: `Match`

#### MatchEventDB
- **Purpose**: Stores individual match events (goals, cards, etc.)
- **Key Fields**: `event_id`, `match_id`, `event_type`, `minute`, `team_id`, `player_name`
- **Relationships**: Many-to-one with `MatchDB`
- **Pydantic Mirror**: `MatchEvent`

#### HighlightDB
- **Purpose**: Stores match highlights and video content
- **Key Fields**: `highlight_id`, `match_id`, `title`, `video_url`, `duration`, `tags`
- **Relationships**: Many-to-one with `MatchDB`
- **Pydantic Mirror**: `Highlight`
- **Note**: `tags` field is stored as JSON array to support list of strings

#### EmojiAssetDB
- **Purpose**: Stores available emoji assets for reactions
- **Key Fields**: `emoji_id`, `emoji_type`, `image_url`, `name`, `is_active`
- **Relationships**: One-to-many with `UserEmojiReactionDB`
- **Pydantic Mirror**: `EmojiAsset`

#### UserEmojiReactionDB
- **Purpose**: Stores user reactions to events
- **Key Fields**: `reaction_id`, `user_id`, `event_id`, `emoji_id`
- **Relationships**: 
  - Many-to-one with `UserDB`
  - Many-to-one with `EmojiAssetDB`
- **Pydantic Mirror**: `UserEmojiReaction`

## Enumerations

All enums are perfectly mirrored between SQLAlchemy and Pydantic:

- **SportTypeEnum** ↔ **SportType**: football, basketball, tennis, cricket, rugby, hockey, baseball
- **MatchStatusEnum** ↔ **MatchStatus**: scheduled, live, finished, cancelled, postponed
- **UserRoleEnum** ↔ **UserRole**: user, admin, moderator
- **EmojiTypeEnum** ↔ **EmojiType**: clap, fire, heart, thumbs_up, celebration, shocked, angry, sad, laugh, goal

## Schema Conversion

The `src/database/schemas.py` module provides conversion functions between SQLAlchemy and Pydantic models:

### Key Conversion Functions

- `convert_user_db_to_response()`: UserDB → UserResponse
- `convert_team_db_to_pydantic()`: TeamDB → Team
- `convert_event_db_to_pydantic()`: EventDB → Event
- `convert_match_db_to_pydantic()`: MatchDB → Match
- `convert_highlight_db_to_pydantic()`: HighlightDB → Highlight
- `convert_emoji_db_to_pydantic()`: EmojiAssetDB → EmojiAsset

### Features

- **Automatic Relationship Loading**: Converts related models (teams in matches, events, etc.)
- **Enum Conversion**: Handles conversion between SQLAlchemy and Pydantic enums
- **JSON Field Handling**: Properly converts JSON fields like preferences, statistics, and tags
- **Optional Field Handling**: Correctly handles nullable fields

## Database Migration

The initial migration (`alembic/versions/001_initial_migration.py`) creates:

1. All enum types in PostgreSQL
2. All tables with proper constraints
3. Foreign key relationships
4. Indexes for performance (email, username)

## Repository Pattern

The `src/database/repositories.py` provides repository classes for each model:

- **UserRepository**: User CRUD operations
- **MatchRepository**: Match queries with filtering and pagination
- **EventRepository**: Event management
- **EmojiRepository**: Emoji and reaction management
- **HighlightRepository**: Highlight queries

## Key Features

### Data Integrity
- Foreign key constraints ensure referential integrity
- Enum constraints ensure valid status/type values
- Unique constraints on email and username

### Performance
- Indexes on frequently queried fields
- Eager loading of relationships via `selectinload()`
- Pagination support in repository methods

### Flexibility
- JSON fields for dynamic data (preferences, statistics, colors)
- Optional fields for extensibility
- Proper handling of timezone-aware datetime fields

## Usage Examples

```python
from src.database import UserDB, MatchDB, convert_match_db_to_pydantic

# Create SQLAlchemy model instance
match_db = await match_repository.get_match_by_id("MATCH123")

# Convert to Pydantic model for API response
match_response = convert_match_db_to_pydantic(match_db)

# Use in FastAPI endpoint
return match_response
```

This architecture ensures that the database models remain in perfect sync with the API contract while providing efficient data access patterns.
