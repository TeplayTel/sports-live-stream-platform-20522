#!/usr/bin/env python3
"""
Startup script for Sports Telecast FastAPI Backend
Runs the server on port 3001 as required by the frontend
"""

import uvicorn
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    # Run the FastAPI application on port 3001
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=3001,
        reload=True,
        log_level="info",
        access_log=True
    )
