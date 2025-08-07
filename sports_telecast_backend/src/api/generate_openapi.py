"""
This file generates and saves the OpenAPI schema for the API application.
It imports the main app object, retrieves the OpenAPI schema, and writes it to a JSON file in a designated directory.
"""

import json
from pathlib import Path

def generate_openapi_schema():
    """Generate and save OpenAPI schema with comprehensive API documentation"""
    try:
        from .main import app
        
        # Generate the OpenAPI schema
        schema = app.openapi()
        
        # Enhance the schema with additional metadata
        schema["info"].update({
            "x-logo": {
                "url": "https://example.com/logo.png",
                "altText": "Sports Telecast API"
            },
            "x-api-id": "sports-telecast-backend",
            "x-audience": "public"
        })
        
        # Add server information
        schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.sportstelecast.com",
                "description": "Production server"
            }
        ]
        
        # Add security schemes
        if "components" not in schema:
            schema["components"] = {}
        
        if "securitySchemes" not in schema["components"]:
            schema["components"]["securitySchemes"] = {}
            
        schema["components"]["securitySchemes"]["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/login or /auth/register"
        }
        
        # Add global security
        schema["security"] = [
            {"bearerAuth": []}
        ]
        
        # Enhance path descriptions
        if "paths" in schema:
            for path, methods in schema["paths"].items():
                for method, spec in methods.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        # Add response examples
                        if "responses" in spec:
                            for status_code, response in spec["responses"].items():
                                if status_code == "200" and "content" in response:
                                    if "application/json" in response["content"]:
                                        # Add example responses based on endpoint
                                        if "/auth/" in path:
                                            response["content"]["application/json"]["example"] = {
                                                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                                "token_type": "bearer",
                                                "expires_in": 86400,
                                                "user": {
                                                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                                                    "email": "user@example.com",
                                                    "username": "sportsfan123"
                                                }
                                            }
                                        elif "/users" in path:
                                            response["content"]["application/json"]["example"] = {
                                                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                                                "email": "user@example.com",
                                                "username": "sportsuser",
                                                "full_name": "Sports Fan",
                                                "role": "user",
                                                "is_active": True,
                                                "created_at": "2024-01-15T10:30:00Z"
                                            }
                                        elif "/matches" in path:
                                            response["content"]["application/json"]["example"] = {
                                                "id": "match123",
                                                "home_team": {"name": "Team A", "short_name": "TEA"},
                                                "away_team": {"name": "Team B", "short_name": "TEB"},
                                                "home_score": 2,
                                                "away_score": 1,
                                                "status": "live",
                                                "start_time": "2024-01-15T15:00:00Z"
                                            }
        
        # Ensure the interfaces directory exists
        interfaces_dir = Path(__file__).parent.parent.parent / "interfaces"
        interfaces_dir.mkdir(exist_ok=True)
        
        # Write the schema to a file
        schema_file = interfaces_dir / "openapi.json"
        with open(schema_file, "w") as f:
            json.dump(schema, f, indent=2, default=str)
            
        print(f"✅ Enhanced OpenAPI schema generated successfully: {schema_file}")
        
        # Generate a summary of endpoints
        endpoint_summary = {
            "total_endpoints": len([path for path_methods in schema.get("paths", {}).values() 
                                  for path in path_methods.keys() if path in ["get", "post", "put", "delete", "patch"]]),
            "endpoints_by_tag": {},
            "security_enabled": bool(schema.get("security")),
            "api_version": schema["info"]["version"]
        }
        
        # Count endpoints by tag
        for path_methods in schema.get("paths", {}).values():
            for method_spec in path_methods.values():
                if isinstance(method_spec, dict) and "tags" in method_spec:
                    for tag in method_spec["tags"]:
                        if tag not in endpoint_summary["endpoints_by_tag"]:
                            endpoint_summary["endpoints_by_tag"][tag] = 0
                        endpoint_summary["endpoints_by_tag"][tag] += 1
        
        print("\n📊 API Summary:")
        print(f"   • Total endpoints: {endpoint_summary['total_endpoints']}")
        print(f"   • Security enabled: {endpoint_summary['security_enabled']}")
        print(f"   • API version: {endpoint_summary['api_version']}")
        print("   • Endpoints by category:")
        for tag, count in endpoint_summary["endpoints_by_tag"].items():
            print(f"     - {tag}: {count} endpoints")
        
        return str(schema_file)
        
    except Exception as e:
        print(f"❌ Error generating OpenAPI schema: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    generate_openapi_schema()
