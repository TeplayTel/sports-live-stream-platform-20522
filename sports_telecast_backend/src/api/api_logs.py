from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


from ..middleware.api_logger import get_api_logger

router = APIRouter(prefix="/api-logs", tags=["API Logs"])

class APICallLog(BaseModel):
    """API call log entry model"""
    timestamp: str = Field(..., description="ISO timestamp of the API call")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="API endpoint path")
    full_url: str = Field(..., description="Complete URL with query parameters")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    status_code: int = Field(..., description="HTTP response status code")
    process_time_ms: float = Field(..., description="Processing time in milliseconds")
    client_ip: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="User agent string")
    request_body: Optional[Any] = Field(None, description="Request body (for POST/PUT requests)")
    response_body: Optional[Any] = Field(None, description="Response body")
    success: bool = Field(..., description="Whether the request was successful (status < 400)")

class APIStats(BaseModel):
    """API statistics model"""
    total_calls: int = Field(..., description="Total number of API calls")
    success_rate: float = Field(..., description="Success rate percentage")
    average_response_time: float = Field(..., description="Average response time in milliseconds")
    endpoints: Dict[str, Dict[str, Any]] = Field(..., description="Per-endpoint statistics")

class APIEndpointInfo(BaseModel):
    """Information about available API endpoints"""
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Endpoint path")
    summary: Optional[str] = Field(None, description="Endpoint summary")
    description: Optional[str] = Field(None, description="Endpoint description")
    tags: List[str] = Field(default_factory=list, description="Endpoint tags")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Parameters")

# PUBLIC_INTERFACE
@router.get("/calls", response_model=List[APICallLog])
async def get_api_calls(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of calls to return"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    path: Optional[str] = Query(None, description="Filter by endpoint path (contains)"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    success_only: Optional[bool] = Query(None, description="Filter successful calls only")
):
    """
    Get recent API call logs
    
    Returns a list of recent API calls with detailed information including:
    - Request details (method, path, parameters, body)
    - Response details (status code, body, processing time)
    - Client information (IP, user agent)
    - Success status and error information
    
    This endpoint is useful for debugging, monitoring, and understanding API usage patterns.
    """
    logger = get_api_logger()
    if not logger:
        raise HTTPException(status_code=503, detail="API logging not initialized")
    
    # Get all calls
    all_calls = logger.get_api_calls(limit=1000)  # Get more for filtering
    
    # Apply filters
    filtered_calls = all_calls
    
    if method:
        filtered_calls = [call for call in filtered_calls if call.get("method", "").upper() == method.upper()]
    
    if path:
        filtered_calls = [call for call in filtered_calls if path.lower() in call.get("path", "").lower()]
    
    if status_code:
        filtered_calls = [call for call in filtered_calls if call.get("status_code") == status_code]
    
    if success_only is not None:
        filtered_calls = [call for call in filtered_calls if call.get("success", False) == success_only]
    
    # Apply limit and return most recent
    return filtered_calls[-limit:] if filtered_calls else []

# PUBLIC_INTERFACE
@router.get("/stats", response_model=APIStats)
async def get_api_stats():
    """
    Get API call statistics
    
    Returns comprehensive statistics about API usage including:
    - Total number of calls made
    - Overall success rate percentage
    - Average response time across all calls
    - Per-endpoint breakdown with individual statistics
    
    This is useful for monitoring API health and performance.
    """
    logger = get_api_logger()
    if not logger:
        raise HTTPException(status_code=503, detail="API logging not initialized")
    
    return logger.get_api_stats()

# PUBLIC_INTERFACE
@router.get("/endpoints", response_model=List[APIEndpointInfo])
async def get_available_endpoints():
    """
    Get list of all available API endpoints
    
    Returns detailed information about all API endpoints including:
    - HTTP methods and paths
    - Endpoint descriptions and summaries
    - Parameter information
    - Grouping tags
    
    This endpoint provides a programmatic way to discover all available APIs.
    """
    from ..main import app
    
    endpoints = []
    
    # Get OpenAPI schema
    openapi_schema = app.openapi()
    paths = openapi_schema.get("paths", {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                endpoint_info = {
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "tags": details.get("tags", []),
                    "parameters": details.get("parameters", [])
                }
                endpoints.append(endpoint_info)
    
    # Sort by path and method
    endpoints.sort(key=lambda x: (x["path"], x["method"]))
    
    return endpoints

# PUBLIC_INTERFACE
@router.get("/clear")
async def clear_api_logs():
    """
    Clear all API call logs
    
    Removes all stored API call logs from memory.
    This is useful for testing or when you want to start fresh monitoring.
    
    Returns the number of logs that were cleared.
    """
    logger = get_api_logger()
    if not logger:
        raise HTTPException(status_code=503, detail="API logging not initialized")
    
    cleared_count = len(logger.api_calls)
    logger.api_calls.clear()
    
    return {
        "message": "API call logs cleared successfully",
        "cleared_count": cleared_count
    }
