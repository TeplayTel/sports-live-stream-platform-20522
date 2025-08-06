#!/usr/bin/env python3
"""
Startup script for Sports Telecast FastAPI Backend
Runs the server on port 3001 as required by the frontend
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the project root to Python path to enable proper imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(project_root)

if __name__ == "__main__":
    # Run the FastAPI application on port 3001 using the correct module path
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=3001,
        reload=True,
        log_level="info",
        access_log=True,
        reload_dirs=[str(project_root / "src")]
    )
