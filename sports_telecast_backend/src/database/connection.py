import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PUBLIC_INTERFACE
# Use only the provided environment variable for DB connection string.
# This backend strictly requires DATABASE_URL or POSTGRES_URL to be set in the environment.
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL or POSTGRES_URL must be set as an environment variable for DB connection. "
        "Hardcoded database connection or localhost is not supported. "
        "Please contact support if you see this error in production."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
