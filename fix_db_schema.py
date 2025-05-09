#!/usr/bin/env python3
"""
Fix database schema issues with the Growatt Devices Monitor database

This script fixes the issue with missing last_update_time column in the devices table
"""

import logging
import psycopg2
from app.config import Config
from app.database import get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_devices_table():
    """
    Fix the devices table by adding the last_update_time column if it doesn't exist
    """
    logger.info("Checking if devices table needs to be fixed...")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if last_update_time column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'devices'
                AND column_name = 'last_update_time'
            """)
            
            has_last_update_time = cursor.fetchone() is not None
            
            if not has_last_update_time:
                logger.info("Adding last_update_time column to devices table...")
                
                # Add the missing column
                cursor.execute("""
                    ALTER TABLE devices 
                    ADD COLUMN last_update_time TIMESTAMP
                """)
                
                # Update existing rows to have a last_update_time value
                cursor.execute("""
                    UPDATE devices
                    SET last_update_time = last_updated
                    WHERE last_update_time IS NULL
                """)
                
                conn.commit()
                logger.info("Successfully added last_update_time column and populated it with values")
                return True
            else:
                logger.info("last_update_time column already exists in devices table, no fix needed")
                return True
                
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error fixing devices table: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error fixing devices table: {e}")
        return False

def main():
    """Main function to run schema fixes"""
    logger.info("Starting database schema fix...")
    
    # Fix devices table
    devices_fixed = fix_devices_table()
    
    if devices_fixed:
        logger.info("Database schema fixes completed successfully!")
    else:
        logger.error("Database schema fixes failed!")
        
    logger.info("Database schema fix script completed")

if __name__ == "__main__":
    main()