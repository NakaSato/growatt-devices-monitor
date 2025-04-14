#!/usr/bin/env python3
"""
Data synchronization script to fetch data from Growatt API and store in the database.
Run this script periodically (e.g., via cron job) to keep the database up to date.
"""

import os
import sys
import json
import logging
import argparse
from datetime import date
from logging import FileHandler
from app.data_collector import GrowattDataCollector
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('data_sync')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Sync data from Growatt API')
    parser.add_argument('--config', type=str, default='config.json', help='Path to config file')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--date', type=str, help='Date for test data (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, help='Output directory for test data')
    parser.add_argument('--log-file', type=str, help='Log to file')
    
    return parser.parse_args()

def load_config(config_path):
    """Load configuration from file"""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Config file not found: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def main():
    """Main function to sync data"""
    args = parse_args()
    config = load_config(args.config)
    
    # Setup file logging if requested
    if args.log_file:
        file_handler = FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    # Get credentials from config or environment
    username = config.get('username', os.environ.get('GROWATT_USERNAME', ''))
    password = config.get('password', os.environ.get('GROWATT_PASSWORD', ''))
    data_dir = config.get('data_dir', 'data')
    
    if not username or not password:
        logger.error("Missing credentials. Please provide username and password.")
        return
    
    try:
        # Initialize database if not in test mode
        if not args.test:
            logger.info("Initializing database...")
            init_db()
        
        # Create data collector
        collector = GrowattDataCollector(
            username=username,
            password=password,
            save_to_file=True,
            data_dir=data_dir
        )
        
        # Collect data based on mode
        if args.test:
            logger.info("Running in test mode...")
            test_options = {
                'data_type': 'daily',
                'test_date': args.date or date.today().strftime("%Y-%m-%d"),
                'dry_run': False,
                'output_dir': args.output or os.path.join(data_dir, 'test')
            }
            result = collector.test_data_collection(test_options)
        else:
            logger.info("Collecting data from Growatt API...")
            result = collector.collect_and_store_all_data()
        
        if result['success']:
            logger.info("Data sync completed successfully.")
        else:
            logger.error(f"Data sync failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"Data sync failed: {str(e)}")
    
    # Clean up file handlers to avoid resource leaks
    for handler in logger.handlers[:]:
        if isinstance(handler, FileHandler):
            handler.close()
            logger.removeHandler(handler)

if __name__ == "__main__":
    main()
