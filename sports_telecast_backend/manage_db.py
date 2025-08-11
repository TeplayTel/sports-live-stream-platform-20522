from src.database.connection import engine
from src.database.models import Base

if __name__ == "__main__":
    # Uses environment-set DATABASE_URL or POSTGRES_URL for all DB operations.
    import sys

    if len(sys.argv) < 2:
        print("Usage: python manage_db.py [create|drop]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        Base.metadata.create_all(bind=engine)
        print("Database tables created.")
    elif command == "drop":
        Base.metadata.drop_all(bind=engine)
        print("Database tables dropped.")
    else:
        print("Unknown command:", command)
