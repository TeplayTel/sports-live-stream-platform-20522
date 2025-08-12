from fastapi import Request
import json

# PUBLIC_INTERFACE
def get_trusted_user(request: Request):
    """
    Extract a trusted user_id and user_data from the incoming request.

    Order of precedence:
      1) Headers (recommended for trusted frontend)
      2) Query parameters
      3) Request body (the route handler should pass parsed body value if needed)

    Accepted keys:
      - Headers: X-User-Id, X-USER-ID, User-Id, X-UserID, userId (case-insensitive)
      - Query params: user_id, userId, user-id, userid
      - User data headers/params: X-User-Data (JSON string) or user_data/userData (query param JSON)

    Note: This helper intentionally does NOT read and consume the request body stream,
    because FastAPI has usually parsed it already into a Pydantic model in the endpoint.
    Endpoint implementations may pass body-derived user_id separately if not present in headers/query.
    """
    # Normalize headers to lowercase for robust lookup
    headers_lower = {k.lower(): v for k, v in request.headers.items()}
    header_keys = ["x-user-id", "x-userid", "user-id", "userid", "user_id", "userid", "userId".lower()]
    user_id = None
    for key in header_keys:
        if key in headers_lower and headers_lower[key]:
            user_id = headers_lower[key]
            break

    # Fallback to query params with common variants
    if not user_id:
        qp = request.query_params
        user_id = qp.get("user_id") or qp.get("userId") or qp.get("user-id") or qp.get("userid")

    # Parse user_data if provided (best-effort)
    user_data = None
    data = headers_lower.get("x-user-data")
    if data:
        try:
            user_data = json.loads(data)
        except Exception:
            user_data = None
    else:
        ud = request.query_params.get("user_data") or request.query_params.get("userData")
        if ud:
            try:
                user_data = json.loads(ud)
            except Exception:
                user_data = None

    return user_id, user_data
