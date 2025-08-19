# Sports Telecast Backend — API Endpoints

This document describes the current API endpoints exposed by the Sports Telecast Backend (FastAPI). It covers methods, paths, inputs and outputs, authentication requirements, and notable behaviors observed directly from the source code.

Base URL
- Default local development: http://localhost:3001
- The service exposes REST endpoints and a WebSocket endpoint under the same base.

CORS
- CORS is enabled with allow_origins = "*", allow_methods = "*", allow_headers = "*".

OpenAPI and Docs
- Swagger UI: GET /docs
- ReDoc: GET /redoc
- OpenAPI JSON: GET /openapi.json

Overview (Mermaid)
The following diagram provides a high-level view of the grouped endpoints.

```mermaid
graph TD
  A["Health"] --> A1["GET /"]
  A --> A2["GET /health/database"]

  B["Authentication (/auth)"] --> B1["POST /auth/login"]
  B --> B2["GET /auth/me"]
  B --> B3["PUT /auth/me"]
  B --> B4["POST /auth/refresh"]

  C["User Profiles (/profiles)"] --> C1["POST /profiles/"]
  C --> C2["GET /profiles/me"]
  C --> C3["PUT /profiles/me"]
  C --> C4["GET /profiles/{profile_id}"]
  C --> C5["GET /profiles/"]
  C --> C6["DELETE /profiles/me"]

  D["Fan Engagement - Emojis (/fan-engagement/emoji/v1)"] --> D1["GET /fan-engagement/emoji/v1/listEmojis"]
  D --> D2["POST /fan-engagement/emoji/v1/userEmojiReaction"]
  D --> D3["GET /fan-engagement/emoji/v1/reactions/{event_id}"]
  D --> D4["POST /fan-engagement/emoji/v1/upload"]

  E["Highlights (/highlights)"] --> E1["GET /highlights/"]
  E --> E2["GET /highlights/{highlight_id}"]
  E --> E3["GET /highlights/featured/latest"]

  F["WebSocket"] --> F1["WS /ws/{event_id}"]
  F --> F2["GET /ws/stats"]
```

Authentication and Authorization

1) JWT Bearer (standard)
- Some endpoints (notably submitting a reaction) require an Authorization: Bearer <token> header.
- Verification is performed by JWTAuth.verify_token; HS256 with SECRET_KEY is used for signed tokens.

2) Mock/Development Tokens (accepted everywhere JWT is used)
- A special mock token is always accepted in dev/test: mock-superuser-jwt-token.
- The mock token can also be provided via environment variable MOCK_JWT_TOKEN; both the configured value and the default are accepted.
- When the mock token is used, the backend returns a payload with admin privileges (role admin, is_admin True, scopes/permissions "*").

3) Trusted User Injection (no JWT required)
- Many endpoints accept a “trusted” user supplied by the frontend without requiring JWT. The user is extracted via headers or query parameters using get_trusted_user.
- Accepted header keys (case-insensitive): X-User-Id, X-USER-ID, User-Id, X-UserID, userId
- Accepted query params: user_id, userId, user-id, userid
- Optional user data can be supplied via X-User-Data (JSON string) or user_data/userData query params (JSON).

4) Admin Token for Emoji Upload
- The multipart upload for emoji assets requires Authorization: Bearer <ADMIN_UPLOAD_TOKEN> or a JWT that confers admin privileges (role or flags).
- ADMIN_UPLOAD_TOKEN is read from environment (.env); defaults to "admin" for local dev.
- A valid JWT that decodes to an admin role (or is_admin True, or "*" scopes/permissions) is also accepted.

Notes on Status Codes
- 200/201: Standard successful responses
- 400: Bad request (e.g., invalid timestamps or unsupported file types)
- 401: Missing or invalid credentials where required
- 403: Insufficient privileges or access to private resources
- 404: Resource not found (e.g., profile or highlight not found)
- 422: Request validation errors (e.g., wrong content type in emoji upload)

Health Endpoints

GET /
- Purpose: General health check with API metadata and a database health snapshot.
- Auth: None
- Response: JSON containing message, status, version, features, endpoints map, and database health.
- Example response (abridged):
  {
    "message": "Sports Telecast Backend API is running!",
    "status": "healthy",
    "version": "1.0.0",
    "database": {...},
    "features": [...],
    "endpoints": {...},
    "documentation": {...}
  }

GET /health/database
- Purpose: Database health check.
- Auth: None
- Response: { "database": <database health object> }

Authentication Endpoints (/auth)

POST /auth/login
- Summary: User login; returns a token and user info. Uses a mock token in this codebase.
- Auth: None
- Body (JSON): UserLogin
  {
    "email": string,
    "password": string
  }
- Response: TokenData
  {
    "access_token": string,
    "token_type": "bearer",
    "expires_in": number,
    "user": UserResponse
  }
- Errors: 401 Invalid email or password

GET /auth/me
- Summary: Get the current user profile using trusted headers or query. No JWT required.
- Auth: Trusted user via headers or query parameters
- Response: UserResponse (user profile)
- Errors: 404 User not found

PUT /auth/me
- Summary: Update the current trusted user's profile.
- Auth: Trusted user via headers or query parameters
- Body (JSON): UserUpdate
- Response: UserResponse (updated)
- Errors: 404 User not found

POST /auth/refresh
- Summary: Returns a fresh mock token and user info for the current trusted user.
- Auth: Trusted user via headers or query parameters
- Response: TokenData
- Errors: 404 User not found

User Profiles (/profiles)

POST /profiles/
- Summary: Create a new user profile.
- Auth: Trusted user via headers or query parameters; if user_id is not present in the body it will be injected from trusted user.
- Body (JSON): UserProfileCreate
- Response: UserProfileResponse
- Errors: 400 profile already exists

GET /profiles/me
- Summary: Get the current trusted user’s profile.
- Auth: Trusted user via headers or query parameters
- Response: UserProfileResponse
- Errors: 404 not found

PUT /profiles/me
- Summary: Update the current trusted user’s profile.
- Auth: Trusted user via headers or query parameters
- Body (JSON): UserProfileUpdate
- Response: UserProfileResponse
- Errors: 404 not found

GET /profiles/{profile_id}
- Summary: Get a user profile by profile ID. Private profiles are only viewable by the owner.
- Auth: Trusted user via headers or query parameters (used to enforce privacy checks)
- Path params: profile_id (string)
- Response: UserProfileResponse
- Errors: 404 not found; 403 if profile is private and not the owner

GET /profiles/
- Summary: Search and list profiles, with optional filters.
- Auth: Optional trusted user; if none is provided, only public profiles are returned.
- Query params:
  - q (string): Search by username/display name
  - favorite_sport (string)
  - location (string)
  - verified_only (bool, default false)
  - limit (1-100, default 20)
  - offset (>=0, default 0)
- Response: List[UserProfileResponse]

DELETE /profiles/me
- Summary: Delete the current trusted user’s profile.
- Auth: Trusted user via headers or query parameters
- Response: { "message": "Profile deleted successfully" }
- Errors: 404 not found

Fan Engagement — Emojis (/fan-engagement/emoji/v1)

GET /fan-engagement/emoji/v1/listEmojis
- Summary: List available emojis with pagination.
- Auth: Optional trusted user (no JWT required)
- Query params:
  - pageNo (>=1, default 1)
  - pageSize (1-100, default 10)
- Response: EmojiListResponse
  {
    "status": "SUCCESS",
    "emojis": [EmojiAsset...],
    "total": number,
    "page": number,
    "page_size": number
  }

POST /fan-engagement/emoji/v1/userEmojiReaction
- Summary: Submit an emoji reaction for an event.
- Auth: Required — Authorization: Bearer <token>
  - Accepts signed JWT or the mock token (mock-superuser-jwt-token)
- Body (JSON): UserEmojiReactionCaptureRequest
  {
    "userId": string,
    "eventId": string,
    "emojiId": string,
    "createdAt": "ISO 8601 timestamp string"  // e.g., 2025-07-29T11:35:24Z
  }
- Response: ReactionCapturedResponse
  {
    "status": "SUCCESS",
    "message": "Reaction captured successfully",
    "data": { "reactionId": "<uuid>" }
  }
- Errors:
  - 400: Missing fields or invalid createdAt format
  - 401: Missing/invalid token
  - 404: Emoji or event not found

GET /fan-engagement/emoji/v1/reactions/{event_id}
- Summary: Get reaction summary for a given event.
- Auth: Optional trusted user
- Path params: event_id (string)
- Response: EmojiReactionSummary
  {
    "event_id": string,
    "emoji_counts": { "<emojiId>": number, ... },
    "total_reactions": number,
    "top_emojis": [ ... ],
    "last_updated": timestamp
  }
- Errors: 404 Event not found (checked against match or event DB)

POST /fan-engagement/emoji/v1/upload
- Summary: Upload a new emoji asset for reactions (admin only for MVP).
- Auth: Required — one of:
  - Authorization: Bearer <ADMIN_UPLOAD_TOKEN>, or
  - Authorization: Bearer <JWT token with admin privileges>, or
  - Authorization: Bearer mock-superuser-jwt-token (dev/test)
- Content-Type: multipart/form-data
  - emojiType: string (identifier-like, max length 32)
  - emojiImage: file (UploadFile) — preferred key is "emojiImage"; "file" is also accepted as a compatibility fallback if provided as an UploadFile
- Response: UploadEmojiResponse
  {
    "status": "SUCCESS",
    "message": "Emoji uploaded successfully",
    "emoji": {
      "emoji_id": string,
      "emoji_type": string,
      "image_url": string
    }
  }
- Errors:
  - 401: Missing/invalid Authorization header
  - 403: Insufficient privileges
  - 400: Unsupported file type
  - 422: Missing the file part or invalid emojiType

Highlights (/highlights)

GET /highlights/
- Summary: Paginated list of highlights.
- Auth: Optional trusted user
- Query params:
  - page (>=1, default 1)
  - page_size (1-100, default 20)
  - match_id (string, optional)
- Response: JSON object (dict) with:
  {
    "highlights": [HighlightResponse...],
    "total": number,
    "page": number,
    "page_size": number
  }

GET /highlights/{highlight_id}
- Summary: Get details for a specific highlight.
- Auth: Optional trusted user
- Path params: highlight_id (string)
- Response: HighlightResponse as a serializable dict
- Errors: 404 if not found

GET /highlights/featured/latest
- Summary: Get the latest featured highlights.
- Auth: Optional trusted user
- Query params:
  - limit (1-50, default 10)
- Response: JSON object (dict) with:
  {
    "highlights": [HighlightResponse...],
    "total": number,
    "page": 1,
    "page_size": limit
  }

WebSocket Endpoints

WS /ws/{event_id}
- Summary: Real-time stream for an event. Sends initial match data and reaction summary; supports ping/pong and fetching reaction summary.
- Auth: Optional token query parameter (?token=<JWT or mock token>)
  - If provided, it is verified; on failure the connection continues without a user_id.
- Path params: event_id (string) — must correspond to a match in DB; otherwise the connection is closed with code 4004.
- On connect:
  - The server sends an "initial_data" message containing match summary and reaction summary.
- Supported client messages:
  - {"type": "ping", "timestamp": "..."} -> server responds with {"type": "pong", "timestamp": "..."}
  - {"type": "get_reaction_summary"} -> server responds with {"type": "reaction_summary", "event_id": "...", "data": {...}}
- Broadcasts:
  - When emoji reactions are captured via REST, the server will broadcast reaction updates to connected clients for the relevant event.

GET /ws/stats
- Summary: Returns counts of active WebSocket connections.
- Auth: None
- Response:
  {
    "total_connections": number,
    "active_events": [event_id...],
    "connection_counts": { "event_id": number, ... }
  }

Removed/Unavailable Routes
- /matches/* — Removed for cricket-only focus (placeholder file exists).
- /users/* — Removed for cricket-only focus (placeholder file exists).
- /api-logs/* — Removed (logging is implemented as middleware only).

Request/Response Schemas (Key Types)

Authentication
- UserLogin: { email: string, password: string }
- TokenData: { access_token, token_type, expires_in, user: UserResponse }
- UserResponse: includes user_id, email, username, role, preferences, is_active, created_at, updated_at
- UserUpdate: allows updating username, full_name, avatar_url, preferences

Profiles
- UserProfileCreate: includes user_id, display_name, bio, location, website, favorite_teams, favorite_sports
- UserProfileUpdate: various optional fields including avatar_url, cover_image_url, visibility, preferences
- UserProfileResponse: full profile details (display fields, preferences, visibility, counters, timestamps)

Emojis
- EmojiListResponse: { status, emojis: [EmojiAsset], total, page, page_size }
- EmojiAsset: { emoji_id, emoji_type, image_url, name, description?, is_active, sort_order, created_at }
- UserEmojiReactionCaptureRequest: { userId, eventId, emojiId, createdAt: ISO 8601 string }
- ReactionCapturedResponse: { status, message, data: { reactionId } }
- EmojiReactionSummary: { event_id, emoji_counts, total_reactions, top_emojis, last_updated }

Highlights
- HighlightResponse includes fields such as id, match_id, title, description, video_url, thumbnail_url, duration, tags, view_count, created_at, updated_at.

Trusted User Injection (Details)
- Headers (case-insensitive): X-User-Id, X-UserID, User-Id, userId
- Query params: user_id, userId, user-id, userid
- Optional user data: X-User-Data (JSON) or user_data/userData (JSON)
- Many endpoints that do not require JWT still derive behavior (like privacy checks) from the trusted user if provided.

Examples

User login
curl -X POST http://localhost:3001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'

List emojis
curl "http://localhost:3001/fan-engagement/emoji/v1/listEmojis?pageNo=1&pageSize=10" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000000"

Capture reaction (requires auth)
curl -X POST http://localhost:3001/fan-engagement/emoji/v1/userEmojiReaction \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock-superuser-jwt-token" \
  -d '{"userId":"<user-uuid>","eventId":"<event-uuid>","emojiId":"<emoji-uuid>","createdAt":"2025-07-29T11:35:24Z"}'

Upload emoji (admin only)
curl -X POST http://localhost:3001/fan-engagement/emoji/v1/upload \
  -H "Authorization: Bearer admin" \
  -F "emojiType=clap" \
  -F "emojiImage=@/path/to/clap.png"

WebSocket connect
wscat -c "ws://localhost:3001/ws/<event_id>?token=mock-superuser-jwt-token"

Special Validation Behavior (Emoji Upload 422)
- The application includes a custom RequestValidationError handler that inspects validation errors for multipart uploads.
- If the field emojiImage is sent as a string instead of a file (UploadFile), the handler returns a tailored 422 response with actionable examples for curl, axios, and fetch, and guidance to use multipart/form-data.
- This behavior is implemented in the global validation_exception_handler in src/api/main.py.

Environment Variables Relevant to API
- JWT_SECRET_KEY: Secret used for signing JWT tokens (HS256). Default "your-secret-key-change-in-production".
- ACCESS_TOKEN_EXPIRE_MINUTES: JWT expiration in minutes. Default 1440 (24h).
- MOCK_JWT_TOKEN: Optional override for the always-accepted mock token; if unset, a default mock token "mock-superuser-jwt-token" is accepted.
- ADMIN_UPLOAD_TOKEN: Token required to authorize the emoji upload endpoint when not using a JWT with admin privileges. Default "admin".
- EMOJI_ASSETS_DIR: Filesystem directory for storing uploaded emoji images. Default "emoji_assets".
- EMOJI_CDN_BASE_URL: Base public URL used to construct the image_url for uploaded/listed emoji assets. Default "https://cdn.placeholderdomain.com/emojis/".
- POSTGRES_URL: SQLAlchemy database URL used by the standalone emoji upload module; defaults to "sqlite:///./test.db" for local/demo.
- HOST: When running src/api/main.py directly, host bind address (default "0.0.0.0").
- PORT: When running src/api/main.py directly, port (default 3001).
