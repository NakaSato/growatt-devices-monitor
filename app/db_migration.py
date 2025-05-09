"""
Database migration utility to add missing columns to existing tables
"""
import logging
from app.database import get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_raw_data_column():
    """
    Add the raw_data JSONB column to the devices table if it doesn't exist
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'devices' AND column_name = 'raw_data'
            """)
            
            if not cursor.fetchone():
                logger.info("Adding raw_data column to devices table...")
                cursor.execute("ALTER TABLE devices ADD COLUMN raw_data JSONB")
                conn.commit()
                logger.info("Successfully added raw_data column to devices table")
            else:
                logger.info("raw_data column already exists in devices table")
            
            return True
            
    except Exception as e:
        logger.error(f"Error adding raw_data column to devices table: {e}")
        return False

def run_migrations():
    """
    Run all database migrations
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        logger.info("Running database migrations...")
        add_raw_data_column()
        logger.info("Database migrations completed")
        return True
    except Exception as e:
        logger.error(f"Database migration error: {e}")
        return False

if __name__ == "__main__":
    run_migrations()
