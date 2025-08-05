#!/usr/bin/env python3
"""
Database initialization script for Sports Telecast Backend
This script can be used to initialize the database tables either through
Alembic migrations or direct table creation.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from database.connection import init_database, check_database_connection, get_database_health
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to initialize database"""
    print("🚀 Sports Telecast Database Initialization")
    print("=" * 50)
    
    try:
        # Check database connection first
        print("🔗 Checking database connection...")
        if await check_database_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
            
        # Get database health info
        health = await get_database_health()
        print(f"📊 Database: {health.get('database')} on {health.get('host')}:{health.get('port')}")
        
        # Initialize database tables
        print("🏗️  Initializing database tables...")
        await init_database()
        print("✅ Database tables initialized successfully")
        
        print("\n🎉 Database initialization completed!")
        print("\nInitialized tables:")
        print("  • users - User accounts and profiles")
        print("  • teams - Sports teams")
        print("  • events - Sports events and tournaments")
        print("  • matches - Individual matches/games")
        print("  • match_events - Match events (goals, cards, etc.)")
        print("  • emoji_assets - Emoji reaction assets")
        print("  • user_emoji_reactions - User emoji reactions")
        print("  • highlights - Match highlights and videos")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
