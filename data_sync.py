#!/usr/bin/env python3
"""
Data synchronization script to fetch data from Growatt API and store in the database.
Run this script periodically (e.g., via cron job) to keep the database up to date.
"""

import logging
import argparse
import os
import sys
from datetime import datetime

# Add the project directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_collector import GrowattDataCollector
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_sync.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run the data synchronization process"""
    parser = argparse.ArgumentParser(description='Sync data from Growatt API to local database')
    parser.add_argument('--init', action='store_true', help='Initialize the database before syncing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Add test mode arguments
    parser.add_argument('--test', action='store_true', help='Run in test mode with simulated data')
    parser.add_argument('--collect', choices=['daily', 'monthly', 'yearly', 'all'], 
                        default='all', help='Specify which data types to collect in test mode')
    parser.add_argument('--date', type=str, help='Simulate data for a specific date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Test process without saving data to database')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Configure test mode logging if needed
    if args.test:
        # Use a different log file for test mode
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                logging.getLogger().removeHandler(handler)
        
        # Add test-specific file handler
        test_file_handler = logging.FileHandler('data_sync_test.log')
        test_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(test_file_handler)
        
        # Create test_data directory if it doesn't exist
        os.makedirs('test_data', exist_ok=True)
        
        logger.info("Running in TEST MODE - No actual API calls will be made")
        if args.collect != 'all':
            logger.info(f"Collecting only {args.collect} data")
        if args.date:
            logger.info(f"Simulating data for date: {args.date}")
        if args.dry_run:
            logger.info("Dry run mode: No data will be saved to the database")
    
    start_time = datetime.now()
    logger.info(f"Starting data synchronization at {start_time}")
    
    # Initialize the database if requested
    if args.init:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized.")
    
    # Create and run the data collector
    collector = GrowattDataCollector()
    
    if args.test:
        # Run in test mode
        test_options = {
            'data_type': args.collect,
            'test_date': args.date,
            'dry_run': args.dry_run,
            'output_dir': 'test_data'
        }
        result = collector.test_data_collection(test_options)
    else:
        # Run normal data collection
        result = collector.collect_and_store_all_data()
    
    if result.get('success'):
        stats = result.get('results', {})
        logger.info(f"Data sync complete. Stats: Plants: {stats.get('plants', 0)}, "
                   f"Devices: {stats.get('devices', 0)}, Energy records: {stats.get('energy_stats', 0)}, "
                   f"Weather records: {stats.get('weather', 0)}")
        
        if stats.get('errors'):
            logger.warning(f"There were {len(stats.get('errors'))} errors during sync")
            for error in stats.get('errors'):
                logger.warning(f"Error: {error}")
    else:
        logger.error(f"Data sync failed: {result.get('message')}")
        
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Data synchronization completed in {duration.total_seconds():.2f} seconds")

if __name__ == "__main__":
    main()
