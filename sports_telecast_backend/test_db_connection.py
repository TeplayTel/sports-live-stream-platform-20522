import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        # Test connection using env variables
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5000")
        db_name = os.getenv("POSTGRES_DB", "myapp")
        db_user = os.getenv("POSTGRES_USER", "appuser")
        db_password = os.getenv("POSTGRES_PASSWORD", "dbuser123")
        
        print(f"Testing connection to: postgresql://{db_user}@{db_host}:{db_port}/{db_name}")
        
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        # Test a simple query
        result = await conn.fetchval("SELECT 1")
        print(f"Connection successful! Query result: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
