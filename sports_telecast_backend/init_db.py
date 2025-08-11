from src.database.connection import engine
from src.database.models import Base

if __name__ == "__main__":
    # Only DATABASE_URL or POSTGRES_URL from environment will work here.
    Base.metadata.create_all(bind=engine)
