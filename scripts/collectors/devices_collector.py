#!/usr/bin/env python3
"""
Devices Collector Script

This script runs the devices data collector to fetch and store device data from the Growatt API.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(parent_dir))

# Import directly from the same directory
from devices_data_collector import DevicesDataCollector, ensure_logs_dir
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'devices_collector.log'))
    ]
)
logger = logging.getLogger("devices_collector")

def main():
    """Main function to run the data collection"""
    # Default API URL
    DEFAULT_API_URL = "http://localhost:8000"
    
    parser = argparse.ArgumentParser(description='Collect Growatt device data and save to database')
    parser.add_argument('--server', type=str, default=DEFAULT_API_URL, 
                        help=f'Server URL (default: {DEFAULT_API_URL})')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Ensure logs directory exists
    ensure_logs_dir()
    
    # Run the data collection
    logger.info(f"Starting device data collection from {args.server}")
    
    try:
        # Initialize collector with specified URL
        collector = DevicesDataCollector(base_url=args.server)
        
        # Run the collection process
        result = collector.run()
        
        if result:
            logger.info("Device data collection completed successfully")
            return 0
        else:
            logger.error("Device data collection failed")
            return 1
    except Exception as e:
        logger.error(f"Error during device data collection: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())