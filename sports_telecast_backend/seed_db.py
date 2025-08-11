from src.database.seed import seed_database

if __name__ == "__main__":
    # All DB connections must be configured via DATABASE_URL or POSTGRES_URL environment variable.
    seed_database()
