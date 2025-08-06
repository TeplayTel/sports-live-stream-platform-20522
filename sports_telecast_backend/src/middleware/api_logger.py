import time
import json
import logging
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Configure API logger
api_logger = logging.getLogger("api_calls")
api_logger.setLevel(logging.INFO)

# Create formatter for structured logging
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create console handler if not exists
if not api_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    api_logger.addHandler(console_handler)

class APILoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests and responses for visibility
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.api_calls = []  # In-memory storage for API calls (consider database for production)
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        
        # Extract request details
        method = request.method
        url = str(request.url)
        path = request.url.path
        query_params = dict(request.query_params)
        headers = dict(request.headers)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Read request body if present (for POST/PUT requests)
        request_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Try to parse as JSON, fallback to string
                    try:
                        request_body = json.loads(body.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_body = body.decode("utf-8", errors="ignore")
            except Exception as e:
                request_body = f"Error reading body: {str(e)}"
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Extract response details
            status_code = response.status_code
            
            # Read response body (create a new response to avoid consuming the original)
            response_body = None
            if hasattr(response, 'body'):
                try:
                    response_body = response.body.decode() if response.body else None
                    if response_body:
                        try:
                            response_body = json.loads(response_body)
                        except json.JSONDecodeError:
                            pass  # Keep as string if not valid JSON
                except Exception:
                    response_body = "Error reading response body"
            
            # Create API call log entry
            api_call_log = {
                "timestamp": timestamp,
                "method": method,
                "path": path,
                "full_url": url,
                "query_params": query_params,
                "status_code": status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "client_ip": client_ip,
                "user_agent": headers.get("user-agent", "unknown"),
                "request_body": request_body,
                "response_body": response_body,
                "success": status_code < 400
            }
            
            # Store in memory (consider database for production)
            self.api_calls.append(api_call_log)
            
            # Keep only last 1000 calls to prevent memory issues
            if len(self.api_calls) > 1000:
                self.api_calls = self.api_calls[-1000:]
            
            # Log the API call
            log_message = (
                f"{method} {path} - {status_code} - "
                f"{api_call_log['process_time_ms']}ms - IP: {client_ip}"
            )
            
            if status_code >= 400:
                api_logger.error(log_message)
            else:
                api_logger.info(log_message)
            
            # Add process time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            error_log = {
                "timestamp": timestamp,
                "method": method,
                "path": path,
                "full_url": url,
                "query_params": query_params,
                "status_code": 500,
                "process_time_ms": round(process_time * 1000, 2),
                "client_ip": client_ip,
                "user_agent": headers.get("user-agent", "unknown"),
                "request_body": request_body,
                "error": str(e),
                "success": False
            }
            
            self.api_calls.append(error_log)
            api_logger.error(f"{method} {path} - ERROR: {str(e)}")
            
            raise e
    
    def get_api_calls(self, limit: int = 100) -> list:
        """Get recent API calls for frontend display"""
        return self.api_calls[-limit:] if self.api_calls else []
    
    def get_api_stats(self) -> dict:
        """Get API statistics"""
        if not self.api_calls:
            return {
                "total_calls": 0,
                "success_rate": 0,
                "average_response_time": 0,
                "endpoints": {}
            }
        
        total_calls = len(self.api_calls)
        successful_calls = sum(1 for call in self.api_calls if call.get("success", False))
        success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 0
        
        # Calculate average response time
        response_times = [call.get("process_time_ms", 0) for call in self.api_calls]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Group by endpoints
        endpoints = {}
        for call in self.api_calls:
            path = call.get("path", "unknown")
            method = call.get("method", "unknown")
            endpoint_key = f"{method} {path}"
            
            if endpoint_key not in endpoints:
                endpoints[endpoint_key] = {
                    "count": 0,
                    "success_count": 0,
                    "avg_response_time": 0
                }
            
            endpoints[endpoint_key]["count"] += 1
            if call.get("success", False):
                endpoints[endpoint_key]["success_count"] += 1
            
            # Update average response time
            current_avg = endpoints[endpoint_key]["avg_response_time"]
            current_count = endpoints[endpoint_key]["count"]
            new_time = call.get("process_time_ms", 0)
            endpoints[endpoint_key]["avg_response_time"] = (
                (current_avg * (current_count - 1) + new_time) / current_count
            )
        
        return {
            "total_calls": total_calls,
            "success_rate": round(success_rate, 2),
            "average_response_time": round(avg_response_time, 2),
            "endpoints": endpoints
        }

# Global instance to access from routes
api_logging_middleware = None

def get_api_logger() -> APILoggingMiddleware:
    """Get the global API logging middleware instance"""
    return api_logging_middleware

def set_api_logger(middleware: APILoggingMiddleware):
    """Set the global API logging middleware instance"""
    global api_logging_middleware
    api_logging_middleware = middleware
