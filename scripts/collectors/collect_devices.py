#!/usr/bin/env python3
"""
Updated version of collect_devices.py with fixes for database foreign key constraints.
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
from datetime import datetime

# Add project root directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

from app.config import Config
from app.database import DatabaseConnector, get_db_connection
from psycopg2.extras import Json

# Import utility functions
sys.path.append(os.path.join(project_root, 'scripts'))
try:
    from utils.utils import retry_with_backoff
except ImportError:
    # Define a simple retry_with_backoff function if the import fails
    def retry_with_backoff(retries=3, backoff_factor=2):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == retries - 1:
                            raise
                        wait_time = backoff_factor ** attempt
                        time.sleep(wait_time)
                return None
            return wrapper
        return decorator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("collect_devices")

def ensure_output_dir(directory="data"):
    """Ensure output directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created output directory at {directory}")
    return directory

class DevicesCollector:
    """Collects device data from the Growatt API and stores it in a local JSON file"""

    def __init__(self, base_url="https://monitoring.boring9.dev", username=None, password=None):
        """
        Initialize the devices collector
        
        Args:
            base_url: Base URL of the Growatt monitoring API
            username: Growatt API username (optional)
            password: Growatt API password (optional)
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.is_authenticated = False
        
    def authenticate(self) -> bool:
        """
        Authenticate with the API
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        if not self.username or not self.password:
            logger.warning("No username/password provided, skipping authentication")
            return True
            
        try:
            url = f"{self.base_url}/api/access"
            response = self.session.post(url, json={
                "username": self.username,
                "password": self.password
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
    
    def fetch_devices(self) -> list:
        """
        Fetch devices from the API
        
        Returns:
            list: List of device data dictionaries
        """
        @retry_with_backoff(retries=3, backoff_factor=2)
        def _fetch():
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
                return devices
            else:
                logger.error(f"Error fetching devices: HTTP {response.status_code} - {response.text}")
                raise Exception(f"HTTP error {response.status_code}")
        
        try:
            return _fetch()
        except Exception as e:
            logger.error(f"Failed to fetch devices after retries: {str(e)}")
            return []
    
    def save_devices_to_file(self, devices: list, output_file: str) -> bool:
        """
        Save devices to a JSON file
        
        Args:
            devices: List of device data dictionaries
            output_file: Path to the output JSON file
            
        Returns:
            bool: True if devices were saved successfully, False otherwise
        """
        if not devices:
            logger.warning("No devices to save")
            return False
        
        try:
            # Prepare data for JSON serialization
            devices_json = []
            for device in devices:
                # Handle datetime objects for serialization
                device_copy = device.copy()
                for key, value in device_copy.items():
                    if isinstance(value, datetime):
                        device_copy[key] = value.isoformat()
                devices_json.append(device_copy)
                
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(devices_json, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Successfully saved {len(devices)} devices to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving devices to file: {str(e)}")
            return False
    
    def save_devices_to_database(self, devices: list) -> bool:
        """
        Save devices to the database
        
        Args:
            devices: List of device data dictionaries
            
        Returns:
            bool: True if devices were saved successfully, False otherwise
        """
        if not devices:
            logger.warning("No devices to save to database")
            return False
        
        try:
            logger.info(f"Saving {len(devices)} devices to database")
            
            # Create a database connector
            db = DatabaseConnector()
            
            # Track success and failures
            success_count = 0
            failed_devices = []
            
            # Track generated IDs to avoid duplicates
            generated_ids = {}
            
            # Begin a database transaction
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if raw_data column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'devices' AND column_name = 'raw_data'
                """)
                raw_data_column_exists = cursor.fetchone() is not None
                
                # Save each device individually with its own transaction
                for device in devices:
                    # Start a new transaction for each device
                    try:
                        # Extract serial number, ensuring it's not None
                        serial_number = device.get('deviceSn') or device.get('deviceId')
                        
                        # Generate a unique ID for devices without serial numbers
                        if not serial_number:
                            # First try to use more reliable identifiers if available
                            # Use a more stable identifier if available (like datalogSn)
                            device_index = device.get('deviceIndex', '')
                            
                            if device.get('datalogSn'):
                                prefix = "datalog"
                                stable_id = device.get('datalogSn')
                                
                                # Add device index if available to make it more unique
                                if device_index:
                                    stable_id = f"{stable_id}_{device_index}"
                            else:
                                # Use plant_id + device index or other attributes
                                prefix = "device"
                                plant_id = str(device.get('plantId', ''))
                                device_type = str(device.get('deviceType', 'unknown'))
                                
                                # Add extra identifiers to make it more unique
                                location_info = ""
                                if device.get('latitude') and device.get('longitude'):
                                    location_info = f"_{str(device.get('latitude'))[:5]}_{str(device.get('longitude'))[:5]}"
                                
                                if device_index:
                                    # Include device index in the ID to distinguish between multiple devices of same type
                                    stable_id = f"{plant_id}_{device_type}_{device_index}{location_info}"
                                else:
                                    stable_id = f"{plant_id}_{device_type}{location_info}"
                            
                            # Generate the base serial number
                            base_serial = f"generated_{prefix}_{stable_id}"
                            
                            # Check if this ID is already used
                            if base_serial in generated_ids:
                                # Add a unique counter to make it unique
                                serial_number = f"{base_serial}_{generated_ids[base_serial]}"
                                generated_ids[base_serial] += 1
                            else:
                                serial_number = base_serial
                                generated_ids[base_serial] = 1
                            
                            # Log at debug level instead of info to reduce log verbosity
                            logger.debug(f"Generated unique identifier for device without serial number: {serial_number}")
                            
                            # Update the device object with this serial number for future reference
                            device['generatedSerialNumber'] = serial_number
                        
                        # Check if the plant exists or if we need to set NULL for plant_id
                        # First check if the plant ID is valid
                        plant_id = device.get('plantId', '')
                        
                        if plant_id:
                            # Check if the plant exists in the database
                            try:
                                cursor.execute("SELECT id FROM plants WHERE id = %s", (plant_id,))
                                plant_exists = cursor.fetchone() is not None
                                
                                if not plant_exists:
                                    # Set plant_id to NULL if it doesn't exist - resolve foreign key constraint issues
                                    logger.warning(f"Plant ID {plant_id} doesn't exist in plants table. Setting to NULL to avoid foreign key constraint error.")
                                    plant_id = None
                            except Exception as plant_check_error:
                                # If there's any error checking the plant, set to NULL to be safe
                                logger.warning(f"Error checking plant existence: {str(plant_check_error)}. Setting plant_id to NULL.")
                                plant_id = None
                        else:
                            # No plant ID provided
                            plant_id = None
                            
                        # Convert device data to the format expected by the database
                        device_data = {
                            'serial_number': serial_number,
                            'plant_id': plant_id,  # This could be NULL if the plant doesn't exist
                            'alias': str(device.get('deviceName', '')),
                            'type': str(device.get('deviceType', '')),
                            'status': str(device.get('status', 'unknown')),
                            'last_update_time': datetime.now(),
                            'raw_data': device
                        }
                        
                        # Save the device
                        self._save_device_to_db(cursor, device_data, raw_data_column_exists)
                        success_count += 1
                        
                        # Commit after each successful device save
                        conn.commit()
                    except Exception as e:
                        # Log the error with details
                        detailed_error = str(e)
                        logger.error(f"Error saving device to database: {detailed_error}")
                        failed_devices.append({"device": device, "error": detailed_error})
                        
                        # Rollback the current transaction
                        conn.rollback()
                
                # Log summary
                if failed_devices:
                    # Extract just the first few failed devices to avoid huge logs
                    sample_failed = failed_devices[:5]
                    sample_errors = [f"{fd['device'].get('deviceName', 'unknown')}: {fd['error'][:50]}..." for fd in sample_failed]
                    
                    logger.warning(f"Failed to save {len(failed_devices)} devices due to database errors.")
                    logger.warning(f"Sample errors: {sample_errors}")
                    
                    # Group errors by type to identify patterns
                    error_types = {}
                    for fd in failed_devices:
                        error_msg = fd['error']
                        error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg[:20]
                        if error_type not in error_types:
                            error_types[error_type] = 0
                        error_types[error_type] += 1
                    
                    # Log error type summary
                    logger.warning(f"Error types: {error_types}")
                
                # Add info about any generated serial numbers
                generated_count = sum(1 for d in devices if not (d.get('deviceSn') or d.get('deviceId')))
                if generated_count > 0:
                    # Group generated identifiers by type
                    datalog_gen_count = sum(1 for d in devices if not (d.get('deviceSn') or d.get('deviceId')) and d.get('datalogSn'))
                    plant_gen_count = generated_count - datalog_gen_count
                    
                    logger.info(f"Generated {generated_count} unique identifiers for devices with missing serial numbers " +
                               f"({datalog_gen_count} using datalogSn, {plant_gen_count} using plantId and device attributes)")
                
                logger.info(f"Successfully saved {success_count}/{len(devices)} devices to database")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Error in database operation: {str(e)}")
            return False
            
    def _save_device_to_db(self, cursor, device_data: dict, raw_data_column_exists: bool) -> None:
        """
        Save a single device to the database.
        
        Args:
            cursor: Database cursor
            device_data: Prepared device data dictionary
            raw_data_column_exists: Whether raw_data column exists in the table
        """
        # Make sure serial_number is valid
        if not device_data.get('serial_number'):
            raise ValueError("Cannot save device with empty serial number")
        
        # Check if the device already exists
        cursor.execute(
            """
            SELECT serial_number FROM devices 
            WHERE serial_number = %s
            """,
            (device_data['serial_number'],)
        )
        exists = cursor.fetchone()
        
        # Handle the case where plant_id is None (no plant association)
        # This avoids foreign key constraint errors
        plant_id_param = device_data['plant_id']
        
        if exists:
            if raw_data_column_exists:
                # Update existing device with raw_data
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
                        plant_id_param,
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time'],
                        Json(device_data['raw_data']) if device_data['raw_data'] else None,
                        device_data['serial_number']
                    )
                )
            else:
                # Update existing device without raw_data
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
                        plant_id_param,
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time'],
                        device_data['serial_number']
                    )
                )
        else:
            if raw_data_column_exists:
                # Insert new device with raw_data
                cursor.execute(
                    """
                    INSERT INTO devices 
                    (serial_number, plant_id, alias, type, status, last_update_time, last_updated, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                    """,
                    (
                        device_data['serial_number'],
                        plant_id_param,
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time'],
                        Json(device_data['raw_data']) if device_data['raw_data'] else None
                    )
                )
            else:
                # Insert new device without raw_data
                cursor.execute(
                    """
                    INSERT INTO devices 
                    (serial_number, plant_id, alias, type, status, last_update_time, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        device_data['serial_number'],
                        plant_id_param,
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time']
                    )
                )
    
    def run(self, output_file: str) -> bool:
        """
        Run the device data collection process
        
        Args:
            output_file: Path to the output JSON file
            
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
            
            # Save devices to file
            if devices:
                if self.save_devices_to_file(devices, output_file):
                    logger.info("Device data collection completed successfully")
                else:
                    logger.error("Failed to save devices to file")
                
                # Save devices to database
                if self.save_devices_to_database(devices):
                    # Count devices that needed generated serial numbers
                    missing_sn_count = sum(1 for d in devices if not (d.get('deviceSn') or d.get('deviceId')))
                    if missing_sn_count > 0:
                        # Get count by type
                        datalog_gen_count = sum(1 for d in devices if not (d.get('deviceSn') or d.get('deviceId')) and d.get('datalogSn'))
                        plant_gen_count = missing_sn_count - datalog_gen_count
                        
                        logger.info(f"Successfully saved all devices to database")
                        logger.debug(f"Device serial number details: {missing_sn_count} devices used generated IDs " +
                                   f"({datalog_gen_count} from datalogSn, {plant_gen_count} from device attributes)")
                    else:
                        logger.info("All devices successfully saved to database with original serial numbers")
                else:
                    logger.error("Failed to save devices to database")
                
                return True
            else:
                logger.warning("No devices to save, collection process completed with no errors")
                return True
        except Exception as e:
            logger.error(f"Error during device data collection: {str(e)}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Collect device data from Growatt API")
    parser.add_argument("--server", dest="server_url", default="https://monitoring.boring9.dev", 
                      help="URL of the server running the Growatt monitor")
    parser.add_argument("--username", dest="username", help="Growatt API username")
    parser.add_argument("--password", dest="password", help="Growatt API password")
    parser.add_argument("--output", dest="output_file", help="Output JSON file path")
    parser.add_argument("--no-db", dest="no_db", action="store_true", 
                      help="Skip saving to database")
    parser.add_argument("--verbose", dest="verbose", action="store_true", 
                      help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Ensure output directory exists
    output_dir = ensure_output_dir()
    
    # Set default output file if not provided
    if not args.output_file:
        output_file = os.path.join(output_dir, f"devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    else:
        output_file = args.output_file
    
    logger.info(f"Starting device data collection from {args.server_url}")
    
    # Initialize collector
    collector = DevicesCollector(
        base_url=args.server_url,
        username=args.username,
        password=args.password
    )
    
    # Run collection
    result = collector.run(output_file)
    
    if result:
        logger.info(f"Device data collection completed successfully: {output_file}")
        print(f"SUCCESS: {output_file}")
        return 0
    else:
        logger.error("Device data collection failed")
        print("ERROR: Device data collection failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
