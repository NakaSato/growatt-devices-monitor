#!/usr/bin/env python3
"""
Create Fault Logs Table

This script creates the fault logs table in the database if it doesn't exist.
This table is used to store device fault logs collected from the Growatt API.

Usage:
    python create_fault_logs_table.py
"""

import os
import sys
import logging

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import app modules
from app.database import get_db_connection
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_fault_logs_table():
    """Create the fault logs table if it doesn't exist"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the table already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'fault_logs'
                );
            """)
            table_exists = cursor.fetchone()['exists']
            
            if table_exists:
                logger.info("Fault logs table already exists, skipping creation")
                return True
            
            # Create the fault logs table
            cursor.execute("""
                CREATE TABLE fault_logs (
                    id SERIAL PRIMARY KEY,
                    plant_id VARCHAR(50) NOT NULL,
                    device_sn VARCHAR(50) NOT NULL,
                    device_name VARCHAR(100),
                    error_code VARCHAR(50),
                    error_msg TEXT,
                    happen_time TIMESTAMP NOT NULL,
                    fault_type INT,
                    raw_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (device_sn, happen_time, error_code)
                );
                
                -- Add indexes for better query performance
                CREATE INDEX idx_fault_logs_plant_id ON fault_logs(plant_id);
                CREATE INDEX idx_fault_logs_device_sn ON fault_logs(device_sn);
                CREATE INDEX idx_fault_logs_happen_time ON fault_logs(happen_time);
            """)
            
            conn.commit()
            logger.info("Successfully created fault logs table")
            return True
    except Exception as e:
        logger.error(f"Error creating fault logs table: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        logger.info("Creating fault logs table...")
        success = create_fault_logs_table()
        if success:
            logger.info("Fault logs table created successfully")
            sys.exit(0)
        else:
            logger.error("Failed to create fault logs table")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Table creation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 