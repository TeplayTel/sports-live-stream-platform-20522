#!/usr/bin/env python3
"""
Database initialization script
Run this to set up the database tables and seed initial data
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from session import init_database
    from seed import seed_database
except ImportError:
    # Try relative imports
    from .session import init_database
    from .seed import seed_database

def main():
    """Initialize database and seed with sample data"""
    try:
        print("Initializing database...")
        
        # Initialize tables
        init_database()
        print("✓ Database tables created successfully")
        
        # Seed with sample data
        seed_database()
        print("✓ Database seeded with sample data")
        
        print("\n🎉 Database initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
