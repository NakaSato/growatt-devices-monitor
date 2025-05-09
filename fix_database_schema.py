#!/usr/bin/env python
"""
Run database migrations to fix schema issues
"""
import sys
import os
import logging

# Set up path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/db_migration.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Run database migrations"""
    logger.info("Running database migration script...")
    
    try:
        # Import the migration module
        from app.db_migration import run_migrations
        
        # Run the migrations
        success = run_migrations()
        
        if success:
            logger.info("Database migration completed successfully")
        else:
            logger.error("Database migration failed")
            return 1
            
    except ImportError as e:
        logger.error(f"Failed to import migration module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
