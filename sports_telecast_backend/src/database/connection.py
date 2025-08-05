from .session import get_db_context, init_database
from .service import DatabaseService
from .seed import seed_database

class DatabaseConnection:
    """
    Database connection wrapper that provides access to database operations
    """
    
    def __init__(self):
        """Initialize database connection"""
        try:
            # Initialize database tables
            init_database()
            print("Database connection established successfully")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def get_service(self) -> DatabaseService:
        """Get database service with session context"""
        # This will be used in dependency injection
        pass

def get_database_service():
    """Dependency to get database service"""
    with get_db_context() as db:
        return DatabaseService(db)

# Initialize database connection
try:
    db_connection = DatabaseConnection()
    
    # Seed database if needed
    try:
        seed_database()
    except Exception as e:
        print(f"Database seeding error (may already be seeded): {e}")
        
except Exception as e:
    print(f"Failed to establish database connection: {e}")
    # Fall back to development mode or handle gracefully
    db_connection = None

# Export the database service getter for use in API endpoints
db = get_database_service
