#!/usr/bin/env python3
"""
Growatt Data Collector Script

This script collects data from the Growatt API and stores it in a PostgreSQL database.
It's designed to be run as a standalone script or scheduled via cron.

Usage:
    python db_data_collector.py [--days-back=7] [--include-weather]

Options:
    --days-back=N           Number of days of historical data to collect (default: 7)
    --include-weather       Include weather data (default: True)
    --help, -h              Show this help message

Environment variables:
    GROWATT_USERNAME        Growatt API username
    GROWATT_PASSWORD        Growatt API password
    POSTGRES_HOST           PostgreSQL host (default: localhost)
    POSTGRES_PORT           PostgreSQL port (default: 5432)
    POSTGRES_USER           PostgreSQL username (default: growatt)
    POSTGRES_PASSWORD       PostgreSQL password (default: growattpassword)
    POSTGRES_DB             PostgreSQL database name (default: growattdb)
    
Example:
    python db_data_collector.py --days-back=14 --include-weather
"""

import os
import sys
import argparse
import logging
from datetime import datetime
import time

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app modules
from app.data_collector import GrowattDataCollector
from app.config import Config
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Collect Growatt data and store in database')
    parser.add_argument('--days-back', type=int, default=7, 
                        help='Number of days of historical data to collect (default: 7)')
    parser.add_argument('--include-weather', action='store_true', default=True,
                        help='Include weather data (default: True)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

def main():
    """Main function to collect and store Growatt data"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    logger.info("Starting Growatt data collection")
    logger.info(f"Days back: {args.days_back}")
    logger.info(f"Include weather: {args.include_weather}")
    
    # Check if credentials are configured
    if not Config.GROWATT_USERNAME or not Config.GROWATT_PASSWORD:
        logger.error("Growatt API credentials not configured. Please set GROWATT_USERNAME and GROWATT_PASSWORD environment variables.")
        sys.exit(1)
    
    # Initialize the database
    logger.info("Initializing database")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)
    
    # Initialize the data collector
    logger.info("Initializing Growatt data collector")
    collector = GrowattDataCollector(
        username=Config.GROWATT_USERNAME,
        password=Config.GROWATT_PASSWORD
    )
    
    # Start time for performance tracking
    start_time = time.time()
    
    # Collect and store data
    logger.info("Starting data collection")
    results = collector.collect_and_store_all_data(
        days_back=args.days_back,
        include_weather=args.include_weather
    )
    
    # Log results
    if results.get("success", False):
        elapsed_time = time.time() - start_time
        logger.info(f"Data collection completed successfully in {elapsed_time:.2f} seconds")
        logger.info(f"Plants collected: {results.get('plants', 0)}")
        logger.info(f"Devices collected: {results.get('devices', 0)}")
        logger.info(f"Energy data points collected: {results.get('energy_data_points', 0)}")
        if args.include_weather:
            logger.info(f"Weather data points collected: {results.get('weather_data_points', 0)}")
    else:
        logger.error(f"Data collection failed: {results.get('message', 'Unknown error')}")
        sys.exit(1)
    
    logger.info("Growatt data collection completed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Data collection interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 