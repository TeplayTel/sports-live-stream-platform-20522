import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """
    Test connection using strict env variables. Will error if any are not set.
    Environment variables required:
      - POSTGRES_HOST     (no default, must be set)
      - POSTGRES_PORT     (should be set to '5001', required)
      - POSTGRES_DB       (no default, must be set)
      - POSTGRES_USER     (no default, must be set)
      - POSTGRES_PASSWORD (no default, must be set)
    """
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    
    missing = [k for k, v in [
        ("POSTGRES_HOST", db_host), 
        ("POSTGRES_PORT", db_port), 
        ("POSTGRES_DB", db_name), 
        ("POSTGRES_USER", db_user), 
        ("POSTGRES_PASSWORD", db_password)
    ] if not v]
    if missing:
        raise RuntimeError(
            f"Missing required env vars for DB connection: {', '.join(missing)}\\n"
            "Please set these in your .env file. See .env.example for required keys."
        )
    print(f"Testing connection to: postgresql://{db_user}@{db_host}:{db_port}/{db_name}")

    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )
        result = await conn.fetchval("SELECT 1")
        print(f"Connection successful! Query result: {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
