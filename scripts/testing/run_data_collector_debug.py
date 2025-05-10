#!/usr/bin/env python3
"""
Growatt Data to SQLite Database Script

This script uses the GrowattDataCollector class to collect data and
ensure it's properly saved to the test_jobs.sqlite database.
"""

import os
import sys
import sqlite3
import json
import logging
import argparse
from datetime import datetime, timedelta

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(parent_dir)

# Import the GrowattDataCollector class
from app.data_collector import GrowattDataCollector
from app.database import get_db_session, init_db
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("growatt_to_sqlite")

# Define the path to the test_jobs.sqlite database
DB_PATH = os.path.join(parent_dir, 'test_jobs.sqlite')


def setup_test_db():
    """Set up a connection to the test SQLite database"""
    logger.info(f"Setting up connection to test database at: {DB_PATH}")
    
    # Temporarily override the database URL to use test_jobs.sqlite
    original_db_url = settings.DATABASE_URL
    settings.DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    # Initialize the database
    init_db()
    
    # Get a database session
    db = get_db_session()
    
    return db, original_db_url


def run_data_collection(debug_mode=False):
    """Run the data collection process with detailed logging"""
    logger.info("Starting data collection process with debug mode")
    
    # Set up the test database
    db, original_db_url = setup_test_db()
    
    try:
        # Create a GrowattDataCollector instance with debug mode
        collector = GrowattDataCollector(db)
        
        # Enable detailed logging if debug mode is on
        if debug_mode:
            collector_logger = logging.getLogger("app.data_collector")
            collector_logger.setLevel(logging.DEBUG)
            
            # Add a specific handler for the collector logger
            debug_handler = logging.StreamHandler()
            debug_handler.setLevel(logging.DEBUG)
            debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(debug_formatter)
            collector_logger.addHandler(debug_handler)
        
        # Track counts before collection
        counts_before = get_db_counts(DB_PATH)
        logger.info(f"Database counts before collection: {counts_before}")
        
        # Run the data collection
        logger.info("Running collect_and_store_all_data method...")
        result = collector.collect_and_store_all_data()
        
        # Track counts after collection
        counts_after = get_db_counts(DB_PATH)
        logger.info(f"Database counts after collection: {counts_after}")
        
        # Calculate and log differences
        diff = {}
        for key in counts_after:
            if key in counts_before:
                diff[key] = counts_after[key] - counts_before[key]
            else:
                diff[key] = counts_after[key]
        
        logger.info(f"Records added during collection: {diff}")
        
        # Verify if data was saved correctly
        if sum(diff.values()) == 0:
            logger.warning("No new records were added to the database during collection!")
            logger.warning("Checking if any data was retrieved but not saved...")
            
            # Check collector's internal counters if available
            if hasattr(collector, 'plants_count'):
                logger.info(f"Collector reported retrieving {collector.plants_count} plants")
            if hasattr(collector, 'devices_count'):
                logger.info(f"Collector reported retrieving {collector.devices_count} devices")
            if hasattr(collector, 'energy_records_count'):
                logger.info(f"Collector reported retrieving {collector.energy_records_count} energy records")
            if hasattr(collector, 'weather_records_count'):
                logger.info(f"Collector reported retrieving {collector.weather_records_count} weather records")
            
            # Check DB connection and commit operations
            logger.info("Verifying database connection and commit operations...")
            verify_db_operations(DB_PATH)
        
        return result
    
    except Exception as e:
        logger.error(f"Error during data collection: {e}", exc_info=True)
        return False
    
    finally:
        # Close the database session
        db.close()
        
        # Restore the original database URL
        settings.DATABASE_URL = original_db_url
        
        logger.info("Data collection process completed")


def get_db_counts(db_path):
    """Get counts of records in each table in the database"""
    counts = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get a list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            counts[table_name] = count
        
        conn.close()
        
    except sqlite3.Error as e:
        logger.error(f"Error getting database counts: {e}")
    
    return counts


def verify_db_operations(db_path):
    """Verify that database operations work correctly by inserting a test record"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create a test table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_db_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP NOT NULL,
            message TEXT
        )
        ''')
        
        # Insert a test record
        timestamp = datetime.now()
        message = "Database operation test"
        cursor.execute('''
        INSERT INTO test_db_operations (timestamp, message)
        VALUES (?, ?)
        ''', (timestamp, message))
        
        # Commit the transaction
        conn.commit()
        
        # Verify the record was inserted
        cursor.execute("SELECT COUNT(*) FROM test_db_operations WHERE message = ?", (message,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info("Database operations are working correctly (test record inserted successfully)")
        else:
            logger.error("Database operations verification failed (test record not found)")
        
        conn.close()
        
    except sqlite3.Error as e:
        logger.error(f"Database operations verification failed with error: {e}")


def examine_data_collector_code():
    """Examine the GrowattDataCollector code to identify potential issues"""
    logger.info("Examining GrowattDataCollector code for potential issues...")
    
    try:
        # Print key methods from the GrowattDataCollector class
        import inspect
        from app.data_collector import GrowattDataCollector
        
        # Get the source code of the collect_and_store_all_data method
        collect_method = inspect.getsource(GrowattDataCollector.collect_and_store_all_data)
        logger.info("collect_and_store_all_data method implementation:")
        print(collect_method)
        
        # Look for specific patterns that might cause issues
        if "commit" not in collect_method:
            logger.warning("No explicit 'commit' found in collect_and_store_all_data method!")
        
        if "session.add" not in collect_method and "session.bulk_save_objects" not in collect_method:
            logger.warning("No session.add or bulk_save_objects found in collect_and_store_all_data method!")
        
    except Exception as e:
        logger.error(f"Error examining code: {e}")


def main():
    """Main function to run the data collection test"""
    parser = argparse.ArgumentParser(description='Test GrowattDataCollector with SQLite database')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--examine-code', action='store_true', help='Examine data collector code')
    
    args = parser.parse_args()
    
    if args.examine_code:
        examine_data_collector_code()
    
    # Run the data collection process
    result = run_data_collection(debug_mode=args.debug)
    
    if result:
        logger.info("Data collection test completed successfully")
        return 0
    else:
        logger.error("Data collection test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())