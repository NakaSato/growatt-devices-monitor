#!/usr/bin/env python3
"""
Fault Logs Collector for Growatt Devices

This script collects fault logs for all Growatt plants and devices and stores them in the database.
It can be run separately from the main data collector to update fault logs at different intervals.

Usage:
    python fault_logs_collector.py [--plant-id=ID] [--days=N]

Options:
    --plant-id=ID      Specific plant ID to collect fault logs for (optional)
    --days=N           Number of days to collect fault logs for (default: 7)
    --help, -h         Show this help message
    --debug            Print raw API responses for debugging
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
import time
import json
from typing import List, Dict, Any, Optional

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import app modules
from app.core.growatt import Growatt
from app.database import DatabaseConnector, get_db_connection
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

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Collect fault logs for Growatt plants and devices')
    parser.add_argument('--plant-id', type=str, help='Specific plant ID to collect fault logs for')
    parser.add_argument('--days', type=int, default=7, help='Number of days to collect fault logs for')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--debug', action='store_true', help='Debug mode - print raw API responses')
    
    return parser.parse_args()

def get_plants(api):
    """Get all plants or a specific plant if plant_id is provided"""
    try:
        plants = api.get_plants()
        if not plants:
            logger.warning("No plants found")
            return []
        return plants
    except Exception as e:
        logger.error(f"Error getting plants: {str(e)}")
        return []

def get_devices_for_plant(api, plant_id):
    """Get all devices for a specific plant"""
    try:
        devices = api.get_devices_by_plant(plant_id)
        if not devices:
            logger.warning(f"No devices found for plant {plant_id}")
            return []
        return devices
    except Exception as e:
        logger.error(f"Error getting devices for plant {plant_id}: {str(e)}")
        return []

def parse_fault_logs(plant_id: str, raw_logs: Dict[str, Any], fault_type: int) -> List[Dict[str, Any]]:
    """
    Parse the raw fault logs response from the API.
    
    Args:
        plant_id: The ID of the plant
        raw_logs: Raw fault logs response from the API
        fault_type: Type of fault log (1=fault, 2=alarm, etc.)
    
    Returns:
        List of parsed fault logs
    """
    parsed_logs = []
    
    if not raw_logs:
        return parsed_logs
    
    # Check if the response has the expected format
    if 'obj' in raw_logs and 'datas' in raw_logs['obj']:
        logs = raw_logs['obj']['datas']
        
        for log in logs:
            try:
                # Parse the timestamp
                happen_time = datetime.strptime(log.get('happenTime', ''), '%Y-%m-%d %H:%M:%S')
                
                # Extract error code from the error message if available
                error_msg = log.get('errorMsg', '')
                error_code = None
                
                # Look for error codes in various formats: "(E01)", "E01:", "Error: E01"
                import re
                code_match = re.search(r'\(([A-Z][0-9]+)\)', error_msg) or \
                             re.search(r'([A-Z][0-9]+):', error_msg) or \
                             re.search(r'Error: ([A-Z][0-9]+)', error_msg) or \
                             re.search(r'([A-Z][0-9]+)', error_msg)
                             
                if code_match:
                    error_code = code_match.group(1)
                
                parsed_logs.append({
                    'plant_id': plant_id,
                    'device_sn': log.get('deviceSn', ''),
                    'device_name': log.get('deviceName', ''),
                    'error_code': error_code,
                    'error_msg': error_msg,
                    'happen_time': happen_time,
                    'fault_type': fault_type,
                    'raw_data': log
                })
            except Exception as e:
                logger.warning(f"Error parsing fault log: {str(e)}")
                # Continue with the next log
    
    return parsed_logs

def collect_fault_logs(api, plant_id=None, days=7, debug=False):
    """
    Collect fault logs for all plants or a specific plant.
    
    Args:
        api: Growatt API instance
        plant_id: Specific plant ID to collect fault logs for (optional)
        days: Number of days to collect fault logs for
        debug: Print raw API responses for debugging
    
    Returns:
        Dictionary with collection statistics
    """
    db = DatabaseConnector()
    plants_data = get_plants(api)
    
    # If a specific plant ID is provided, filter the plants list
    if plant_id:
        plants_data = [p for p in plants_data if p.get('id') == plant_id]
        if not plants_data:
            logger.error(f"Plant with ID {plant_id} not found")
            return {'success': False, 'message': f"Plant with ID {plant_id} not found"}
    
    # Generate a list of dates to collect logs for
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    
    # Statistics
    stats = {
        'success': True,
        'plants_processed': 0,
        'fault_logs_collected': 0,
        'dates_processed': len(dates)
    }
    
    # Limit to a small number of plants if in debug mode
    if debug and len(plants_data) > 2:
        logger.info(f"Debug mode: limiting to first 2 plants out of {len(plants_data)}")
        plants_data = plants_data[:2]
    
    for plant in plants_data:
        plant_id = plant.get('id')
        plant_name = plant.get('plantName', 'Unknown')
        
        logger.info(f"Collecting fault logs for plant: {plant_name} (ID: {plant_id})")
        
        # Fault log collection counters for this plant
        plant_fault_logs = 0
        
        # Collect faults and alarms for each date
        for date in dates:
            logger.info(f"Collecting fault logs for date: {date}")
            
            # Collect fault logs (type 1 = faults)
            try:
                fault_logs_response = api.get_fault_logs(
                    plantId=plant_id,
                    date=date,
                    device_sn="",  # Empty = all devices
                    page_num=1,
                    device_flag=0,  # 0 = all devices
                    fault_type=1  # 1 = faults
                )
                
                if debug:
                    logger.debug(f"Raw fault logs response: {json.dumps(fault_logs_response, indent=2)}")
                
                parsed_faults = parse_fault_logs(plant_id, fault_logs_response, fault_type=1)
                if parsed_faults:
                    saved_count = db.save_fault_logs(parsed_faults)
                    plant_fault_logs += saved_count
                    logger.info(f"Saved {saved_count} fault logs for date {date}")
            except Exception as e:
                logger.error(f"Error collecting fault logs for plant {plant_name} on date {date}: {str(e)}")
            
            # Collect alarm logs (type 2 = alarms)
            try:
                alarm_logs_response = api.get_fault_logs(
                    plantId=plant_id,
                    date=date,
                    device_sn="",  # Empty = all devices
                    page_num=1,
                    device_flag=0,  # 0 = all devices
                    fault_type=2  # 2 = alarms
                )
                
                if debug:
                    logger.debug(f"Raw alarm logs response: {json.dumps(alarm_logs_response, indent=2)}")
                
                parsed_alarms = parse_fault_logs(plant_id, alarm_logs_response, fault_type=2)
                if parsed_alarms:
                    saved_count = db.save_fault_logs(parsed_alarms)
                    plant_fault_logs += saved_count
                    logger.info(f"Saved {saved_count} alarm logs for date {date}")
            except Exception as e:
                logger.error(f"Error collecting alarm logs for plant {plant_name} on date {date}: {str(e)}")
        
        logger.info(f"Collected a total of {plant_fault_logs} fault logs for plant {plant_name}")
        stats['fault_logs_collected'] += plant_fault_logs
        stats['plants_processed'] += 1
    
    return stats

def main():
    """Main function to collect fault logs"""
    args = parse_arguments()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate Growatt credentials
    if not Config.GROWATT_USERNAME or not Config.GROWATT_PASSWORD:
        logger.error("Growatt API credentials not configured")
        sys.exit(1)
    
    # Initialize Growatt API
    api = Growatt()
    
    # Try to authenticate
    try:
        login_success = api.login(Config.GROWATT_USERNAME, Config.GROWATT_PASSWORD)
        if not login_success:
            logger.error("Failed to authenticate with Growatt API")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        sys.exit(1)
    
    logger.info("Successfully authenticated with Growatt API")
    
    # Start time for performance tracking
    start_time = time.time()
    
    # Collect fault logs
    stats = collect_fault_logs(api, args.plant_id, args.days, args.debug)
    
    # Log results
    elapsed_time = time.time() - start_time
    logger.info(f"Fault logs collection completed in {elapsed_time:.2f} seconds")
    logger.info(f"Plants processed: {stats['plants_processed']}")
    logger.info(f"Fault logs collected: {stats['fault_logs_collected']}")
    logger.info(f"Dates processed: {stats['dates_processed']}")
    
    # Logout from API
    try:
        api.logout()
        logger.info("Successfully logged out from Growatt API")
    except Exception as e:
        logger.warning(f"Error during logout: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Fault logs collection interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 