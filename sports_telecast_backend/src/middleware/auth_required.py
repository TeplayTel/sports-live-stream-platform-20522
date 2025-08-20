from typing import Callable, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os

from ..auth.jwt_auth import JWTAuth


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces JWT authentication on all HTTP requests except a small
    set of explicitly allowed endpoints.

    Exemptions:
      - POST /auth/register
      - POST /auth/login
      - GET  /openapi.json
      - GET  /docs (and nested paths)
      - GET  /redoc (and nested paths)

    Special handling:
      - POST /fan-engagement/emoji/v1/upload
        Accepts either a valid JWT or a static ADMIN_UPLOAD_TOKEN for backwards
        compatibility with the upload script. Other endpoints do NOT accept
        the static token and require a valid JWT.

    Notes:
      - This middleware applies only to HTTP routes (scope 'http'). WebSockets
        require separate handling within the route handlers.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Exact path exemptions (method-agnostic; keep minimal per requirement)
        self.exempt_paths = {
            "/auth/register",
            "/auth/login",
            "/openapi.json",  # Allow OpenAPI spec without auth
        }
        # Prefix-based exemptions to allow FastAPI docs UIs and any nested assets
        self.exempt_prefixes = ["/docs", "/redoc"]

        # Path for upload which may accept ADMIN_UPLOAD_TOKEN
        self.upload_path = "/fan-engagement/emoji/v1/upload"
        # Admin token for upload endpoint compatibility
        self.admin_upload_token = os.getenv("ADMIN_UPLOAD_TOKEN", "admin")

    async def dispatch(self, request: Request, call_next: Callable):
        # Only handle HTTP scope
        if request.scope.get("type") != "http":
            return await call_next(request)

        path = request.url.path

        # Allow CORS preflight requests
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        # Exempt specific paths (login/register, openapi) and docs prefixes
        if path in self.exempt_paths or any(path.startswith(prefix) for prefix in getattr(self, "exempt_prefixes", [])):
            return await call_next(request)

        # Extract Authorization header
        auth_header: Optional[str] = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return self._unauthorized_response("Authorization header missing or invalid")

        token = auth_header.split(" ", 1)[1].strip()

        # Special-case the emoji upload endpoint: accept ADMIN_UPLOAD_TOKEN OR valid JWT
        if path == self.upload_path and token == (self.admin_upload_token or ""):
            # Allow through without JWT verification
            return await call_next(request)

        # Otherwise, require a valid JWT
        try:
            payload = JWTAuth.verify_token(token)
            # Attach payload to request.state for downstream usage if needed
            request.state.user = payload
        except Exception:
            return self._unauthorized_response("Could not validate credentials")

        return await call_next(request)

    @staticmethod
    def _unauthorized_response(message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": message},
            headers={"WWW-Authenticate": "Bearer"},
        )
