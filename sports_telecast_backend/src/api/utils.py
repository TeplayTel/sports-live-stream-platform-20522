from fastapi import Request
import json

# PUBLIC_INTERFACE
def get_trusted_user(request: Request):
    """
    Extract a trusted user_id and user_data from request.
    Order of precedence: headers > query params > request body.
    Headers: X-User-Id (userId), X-User-Data (userData as JSON string)
    """
    user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id") or None
    user_data = None
    data = request.headers.get("X-User-Data")
    if data:
        try:
            user_data = json.loads(data)
        except Exception:
            user_data = None
    else:
        ud = request.query_params.get("user_data")
        if ud:
            try:
                user_data = json.loads(ud)
            except Exception:
                user_data = None
    return user_id, user_data
