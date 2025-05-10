#!/usr/bin/env python3
"""
Devices Data Collector

This script implements a data collector for Growatt devices.
It fetches device data from the API and stores it in the PostgreSQL database.
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Import from the app for configuration
from app.config import Config
from app.database import DatabaseConnector, get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'devices_data_collector.log'))
    ]
)
logger = logging.getLogger("devices_data_collector")

def ensure_logs_dir():
    """Ensure logs directory exists"""
    logs_dir = os.path.join(parent_dir, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        logger.info(f"Created logs directory at {logs_dir}")

class DevicesDataCollector:
    """Collects device data from the Growatt API and stores it in the PostgreSQL database"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the devices data collector
        
        Args:
            base_url: Base URL of the Growatt monitoring API
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.is_authenticated = False
        
        # Initialize DatabaseConnector
        self.db = DatabaseConnector()
        
    def authenticate(self) -> bool:
        """
        Authenticate with the API
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/access"
            response = self.session.post(url, json={
                "username": Config.GROWATT_USERNAME,
                "password": Config.GROWATT_PASSWORD
            })
            
            if response.status_code == 200:
                auth_result = response.json()
                if auth_result.get("status") == "success":
                    self.is_authenticated = True
                    logger.info("Authentication successful")
                    return True
                else:
                    logger.error(f"Authentication failed with status: {auth_result.get('status')}")
            else:
                logger.error(f"Authentication failed with status code {response.status_code}: {response.text}")
                
            return False
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
    
    def fetch_devices(self) -> List[Dict[str, Any]]:
        """
        Fetch devices from the API
        
        Returns:
            List[Dict[str, Any]]: List of device data dictionaries
        """
        devices = []
        retries = 3
        
        for attempt in range(retries):
            try:
                url = f"{self.base_url}/api/devices"
                response = self.session.get(url)
                
                if response.status_code == 200:
                    devices = response.json()
                    if not devices and isinstance(devices, list):
                        logger.warning("No devices returned from the API")
                    elif not isinstance(devices, list):
                        logger.error(f"Unexpected response format: {type(devices)}")
                        devices = []
                    else:
                        logger.info(f"Successfully fetched {len(devices)} devices")
                    break
                else:
                    logger.error(f"Error fetching devices: HTTP {response.status_code} - {response.text}")
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Exception while fetching devices: {str(e)}")
                if attempt < retries - 1:
                    logger.info(f"Retrying... (attempt {attempt + 1}/{retries})")
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return devices

    def save_devices_to_db(self, devices: List[Dict[str, Any]]) -> bool:
        """
        Save devices to the PostgreSQL database
        
        Args:
            devices: List of device data dictionaries
            
        Returns:
            bool: True if devices were saved successfully, False otherwise
        """
        if not devices:
            logger.warning("No devices to save")
            return False
        
        try:
            # Prepare all devices for saving
            devices_to_save = []
            
            for device_index, device in enumerate(devices):
                try:
                    # Skip if device is not a dictionary
                    if not isinstance(device, dict):
                        logger.warning(f"Skipping non-dictionary device: {type(device)}")
                        continue
                    
                    # Use 'sn' field if 'serial_number' doesn't exist
                    serial_number = device.get('serial_number') or device.get('sn')
                    
                    # Skip if missing required fields
                    if not serial_number:
                        logger.warning(f"Skipping device missing serial_number/sn: {device}")
                        continue
                        
                    # Determine device type from deviceModel or model
                    device_type = ''
                    if device.get('deviceModel'):
                        device_type = device.get('deviceModel')
                    elif device.get('deviceType'):
                        device_type = str(device.get('deviceType', ''))
                    else:
                        device_type = device.get('model', '')
                    
                    # Get last_update_time
                    last_update_time = device.get('last_update_time') or device.get('lastUpdateTime')
                    if isinstance(last_update_time, str):
                        try:
                            last_update_time = datetime.fromisoformat(last_update_time.replace('Z', '+00:00'))
                        except ValueError:
                            logger.warning(f"Invalid datetime format for last_update_time: {last_update_time}")
                            last_update_time = datetime.now()
                    else:
                        last_update_time = datetime.now()
                    
                    # Create a properly formatted device record
                    single_device = {
                        'serial_number': serial_number,
                        'plant_id': device.get('plant_id', '') or device.get('plantId', ''),
                        'alias': device.get('alias', '') or device.get('deviceName', ''),
                        'type': device_type,
                        'status': device.get('status', 'unknown'),
                        'last_update_time': last_update_time,
                        'raw_data': device  # Store the entire device data
                    }
                    
                    # Add to the list of prepared devices
                    devices_to_save.append(single_device)
                
                except Exception as e:
                    logger.error(f"Error processing device {device_index}: {str(e)}")
            
            # Now save all processed devices to the database
            if not devices_to_save:
                logger.warning("No valid devices to save after processing")
                return False
            
            # Save all devices to the database in a batch
            try:
                # Need to use with statement with get_db_connection()
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    saved_count = 0
                    
                    for device in devices_to_save:
                        # Check for required fields
                        if not all(k in device for k in ['serial_number', 'plant_id', 'alias', 'type', 'status']):
                            logger.warning(f"Device data missing required fields: {device}")
                            continue
                        
                        # Prepare raw_data as JSON
                        raw_data = json.dumps(device.get('raw_data', {}))
                        
                        # Check if raw_data column exists
                        cursor.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'devices' AND column_name = 'raw_data'
                        """)
                        raw_data_column_exists = cursor.fetchone() is not None
                        
                        # Check if device exists
                        cursor.execute(
                            "SELECT serial_number FROM devices WHERE serial_number = %s",
                            (device['serial_number'],)
                        )
                        exists = cursor.fetchone()
                        
                        if exists:
                            if raw_data_column_exists:
                                # Update with raw_data
                                cursor.execute(
                                    """
                                    UPDATE devices 
                                    SET plant_id = %s,
                                        alias = %s,
                                        type = %s,
                                        status = %s,
                                        last_update_time = %s,
                                        last_updated = NOW(),
                                        raw_data = %s
                                    WHERE serial_number = %s
                                    """,
                                    (
                                        device['plant_id'],
                                        device['alias'],
                                        device['type'],
                                        device['status'],
                                        device['last_update_time'],
                                        raw_data,
                                        device['serial_number']
                                    )
                                )
                            else:
                                # Update without raw_data
                                cursor.execute(
                                    """
                                    UPDATE devices 
                                    SET plant_id = %s,
                                        alias = %s,
                                        type = %s,
                                        status = %s,
                                        last_update_time = %s,
                                        last_updated = NOW()
                                    WHERE serial_number = %s
                                    """,
                                    (
                                        device['plant_id'],
                                        device['alias'],
                                        device['type'],
                                        device['status'],
                                        device['last_update_time'],
                                        device['serial_number']
                                    )
                                )
                        else:
                            if raw_data_column_exists:
                                # Insert with raw_data
                                cursor.execute(
                                    """
                                    INSERT INTO devices 
                                    (serial_number, plant_id, alias, type, status, last_update_time, last_updated, raw_data)
                                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                                    """,
                                    (
                                        device['serial_number'],
                                        device['plant_id'],
                                        device['alias'],
                                        device['type'],
                                        device['status'],
                                        device['last_update_time'],
                                        raw_data
                                    )
                                )
                            else:
                                # Insert without raw_data
                                cursor.execute(
                                    """
                                    INSERT INTO devices 
                                    (serial_number, plant_id, alias, type, status, last_update_time, last_updated)
                                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                    """,
                                    (
                                        device['serial_number'],
                                        device['plant_id'],
                                        device['alias'],
                                        device['type'],
                                        device['status'],
                                        device['last_update_time']
                                    )
                                )
                        
                        saved_count += 1
                        logger.debug(f"Successfully saved device {device['serial_number']}")
                    
                    # Commit all changes
                    conn.commit()
                    logger.info(f"Successfully saved {saved_count} devices to the database")
                    return saved_count > 0
                
            except Exception as db_error:
                logger.error(f"Database error saving devices: {str(db_error)}")
                return False
        
        except Exception as e:
            logger.error(f"Error saving devices to database: {str(e)}")
            return False
    
    def run(self) -> bool:
        """
        Run the device data collection process
        
        Returns:
            bool: True if the collection was successful, False otherwise
        """
        try:
            # Authenticate with the API
            if not self.is_authenticated and not self.authenticate():
                logger.error("Failed to authenticate with the API")
                return False
            
            # Fetch devices
            devices = self.fetch_devices()
            
            # Save devices to the database
            if devices:
                if self.save_devices_to_db(devices):
                    logger.info("Device data collection completed successfully")
                    return True
                else:
                    logger.error("Failed to save devices to the database")
                    return False
            else:
                logger.warning("No devices to save, collection process completed with no errors")
                return True
        except Exception as e:
            logger.error(f"Error during device data collection: {str(e)}")
            return False

def run_collection() -> bool:
    """
    Run the device data collection process
    
    Returns:
        bool: True if the collection was successful, False otherwise
    """
    try:
        # Ensure logs directory exists
        ensure_logs_dir()
        
        # Initialize collector with production URL
        default_url = "https://monitoring.boring9.dev"
        collector = DevicesDataCollector(base_url=default_url)
        
        # Run collection
        logger.info("Starting device data collection")
        result = collector.run()
        
        if result:
            logger.info("Device data collection completed successfully")
        else:
            logger.error("Device data collection failed")
        
        return result
    except Exception as e:
        logger.error(f"Error in run_collection: {str(e)}")
        return False

if __name__ == "__main__":
    run_collection() 