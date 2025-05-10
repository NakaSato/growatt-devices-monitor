#!/usr/bin/env python3
"""
Script to create a notification history table to track when notifications were last sent.

This script adds a new table 'notification_history' to the database to track when 
notifications were last sent for each device, allowing for better cooldown management.

Usage:
    python setup_notification_history.py [--debug]
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Configure logging to write to file
LOG_FILE = "logs/setup_notification_history.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def setup_notification_history_table():
    """
    Create the notification_history table if it doesn't exist
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        from app.database import DatabaseConnector
        
        # Initialize database connector
        db = DatabaseConnector()
        
        # Create notification_history table
        create_table_query = """
            CREATE TABLE IF NOT EXISTS notification_history (
                id SERIAL PRIMARY KEY,
                device_serial_number TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                message TEXT,
                success BOOLEAN NOT NULL DEFAULT TRUE,
                FOREIGN KEY (device_serial_number) REFERENCES devices (serial_number)
            )
        """
        
        if not db.execute(create_table_query):
            logger.error("Failed to create notification_history table")
            return False
        
        # Create indexes for faster lookups
        create_index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_notification_history_device ON notification_history(device_serial_number)",
            "CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at ON notification_history(sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_notification_history_type ON notification_history(notification_type)"
        ]
        
        for query in create_index_queries:
            if not db.execute(query):
                logger.warning(f"Failed to create index with query: {query}")
                # Continue even if index creation fails
            
        logger.info("Notification history table created successfully")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating notification history table: {e}")
        return False

def main():
    """
    Main function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Setup notification history table in database")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        logger.info("Starting setup of notification history table")
        
        success = setup_notification_history_table()
        
        if success:
            logger.info("Notification history table setup completed successfully")
            return 0
        else:
            logger.error("Failed to setup notification history table")
            return 1
        
    except Exception as e:
        logger.error(f"Error in notification history table setup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
