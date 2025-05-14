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
        logging.FileHandler(os.path.join('logs', 'collect_devices_data.log'))
    ]
)
logger = logging.getLogger("collect_devices_data")

def ensure_logs_dir():
    """Ensure logs directory exists"""
    logs_dir = os.path.join(parent_dir, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        logger.info(f"Created logs directory at {logs_dir}")

class DevicesDataCollector:
    """Collects device data from the Growatt API and stores it in the PostgreSQL database"""

    def __init__(self, base_url: str = "https://monitoring.boring9.dev"):
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
    
    def update_device_by_id(self, device_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a device in the database by its serial number
        
        Args:
            device_id: Serial number of the device to update
            update_data: Dictionary containing fields to update
            
        Returns:
            bool: True if device was updated successfully, False otherwise
        """
        if not device_id:
            logger.error("Device ID (serial number) is required for update")
            return False
            
        if not update_data:
            logger.warning("No update data provided")
            return False
            
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First check if device exists
                cursor.execute(
                    "SELECT serial_number FROM devices WHERE serial_number = %s",
                    (device_id,)
                )
                exists = cursor.fetchone()
                
                if not exists:
                    logger.error(f"Device with ID {device_id} not found")
                    return False
                
                # Prepare update fields and values
                update_fields = []
                update_values = []
                
                # Map of field names to database column names
                field_mapping = {
                    'plant_id': 'plant_id',
                    'alias': 'alias',
                    'type': 'type',
                    'status': 'status',
                    'last_update_time': 'last_update_time'
                }
                
                # Add raw_data if it exists
                has_raw_data = False
                if 'raw_data' in update_data:
                    update_fields.append('raw_data = %s')
                    update_values.append(json.dumps(update_data['raw_data']))
                    has_raw_data = True
                
                # Add other fields
                for field, value in update_data.items():
                    if field in field_mapping and field != 'raw_data':
                        update_fields.append(f"{field_mapping[field]} = %s")
                        update_values.append(value)
                
                # Always update last_updated timestamp
                update_fields.append("last_updated = NOW()")
                
                # If no fields to update (other than timestamp), return False
                if not update_fields:
                    logger.warning(f"No valid fields to update for device {device_id}")
                    return False
                
                # Build the SQL query
                sql = f"""
                UPDATE devices 
                SET {', '.join(update_fields)}
                WHERE serial_number = %s
                """
                
                # Add the device_id as the last parameter for the WHERE clause
                update_values.append(device_id)
                
                # Execute the update
                cursor.execute(sql, tuple(update_values))
                
                # Check if a row was updated
                if cursor.rowcount > 0:
                    logger.info(f"Successfully updated device {device_id}")
                    return True
                else:
                    logger.warning(f"Device {device_id} exists but no rows were updated")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating device by ID: {str(e)}")
            return False
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a device from the database by its ID (serial number)
        
        Args:
            device_id: The serial number of the device to retrieve
            
        Returns:
            Dict[str, Any]: Device data if found, None otherwise
        """
        if not device_id:
            logger.error("Device ID is required")
            return None
            
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT * FROM devices
                    WHERE serial_number = %s
                    """,
                    (device_id,)
                )
                
                device = cursor.fetchone()
                
                if device:
                    logger.info(f"Found device with ID {device_id}")
                    return dict(device)
                else:
                    logger.warning(f"No device found with ID {device_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting device by ID: {str(e)}")
            return None
    
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

def update_device_by_id_cli(device_id: str, update_fields: Dict[str, Any]) -> bool:
    """
    Update a device in the database by its ID via CLI
    
    Args:
        device_id: Serial number of the device to update
        update_fields: Dictionary containing fields to update
        
    Returns:
        bool: True if device was updated successfully, False otherwise
    """
    try:
        # Ensure logs directory exists
        ensure_logs_dir()
        
        # Initialize collector with production URL
        default_url = "https://monitoring.boring9.dev"
        collector = DevicesDataCollector(base_url=default_url)
        
        # Update device by ID
        logger.info(f"Updating device with ID {device_id}")
        result = collector.update_device_by_id(device_id, update_fields)
        
        if result:
            logger.info(f"Device {device_id} updated successfully")
        else:
            logger.error(f"Failed to update device {device_id}")
        
        return result
    except Exception as e:
        logger.error(f"Error in update_device_by_id_cli: {str(e)}")
        return False

def get_device_by_id_cli(device_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a device from the database by its ID via CLI
    
    Args:
        device_id: Serial number of the device to retrieve
        
    Returns:
        Dict[str, Any]: Device data if found, None otherwise
    """
    try:
        # Ensure logs directory exists
        ensure_logs_dir()
        
        # Initialize collector with production URL
        default_url = "https://monitoring.boring9.dev"
        collector = DevicesDataCollector(base_url=default_url)
        
        # Get device by ID
        logger.info(f"Getting device with ID {device_id}")
        device = collector.get_device_by_id(device_id)
        
        if device:
            logger.info(f"Device {device_id} retrieved successfully")
        else:
            logger.error(f"Device {device_id} not found")
        
        return device
    except Exception as e:
        logger.error(f"Error in get_device_by_id_cli: {str(e)}")
        return None

def export_devices_to_json(output_file: str) -> bool:
    """
    Export all devices from the database to a JSON file
    
    Args:
        output_file: Path to the output JSON file
        
    Returns:
        bool: True if export was successful, False otherwise
    """
    try:
        # Initialize collector
        collector = DevicesDataCollector()
        
        # Get all devices from the database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM devices")
            devices = cursor.fetchall()
            
            if not devices:
                logger.warning("No devices found in the database to export")
                return False
                
            # Convert to list of dictionaries
            devices_list = [dict(device) for device in devices]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Write to file
            with open(output_file, 'w') as f:
                # Handle datetime serialization
                json.dump(devices_list, f, indent=2, default=str)
                
            logger.info(f"Successfully exported {len(devices_list)} devices to {output_file}")
            return True
            
    except Exception as e:
        logger.error(f"Error exporting devices to JSON: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Growatt Devices Data Collector")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # 'collect' command
    collect_parser = subparsers.add_parser("collect", help="Collect device data from API")
    
    # 'update' command
    update_parser = subparsers.add_parser("update", help="Update device by ID")
    update_parser.add_argument("device_id", help="Device ID (serial number)")
    update_parser.add_argument("--plant-id", help="Plant ID")
    update_parser.add_argument("--alias", help="Device alias")
    update_parser.add_argument("--type", help="Device type")
    update_parser.add_argument("--status", help="Device status")
    update_parser.add_argument("--from-json", help="Update from JSON file")
    update_parser.add_argument("--show", action="store_true", help="Show device after update")
    
    # 'get' command
    get_parser = subparsers.add_parser("get", help="Get device by ID")
    get_parser.add_argument("device_id", help="Device ID (serial number)")
    get_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    # 'export' command
    export_parser = subparsers.add_parser("export", help="Export devices from database to JSON")
    export_parser.add_argument("--output", help="Output JSON file path", required=True)
    
    args = parser.parse_args()
    
    if args.command == "collect" or not args.command:
        # Default action is to collect data
        run_collection()
    elif args.command == "update":
        # Build update data from arguments
        update_data = {}
        
        # Load from JSON file if specified
        if args.from_json:
            try:
                with open(args.from_json, 'r') as f:
                    update_data = json.load(f)
                print(f"Loaded update data from {args.from_json}")
            except Exception as e:
                print(f"Error loading JSON file: {e}")
                sys.exit(1)
        else:
            # Build from command line arguments
            if args.plant_id:
                update_data["plant_id"] = args.plant_id
            if args.alias:
                update_data["alias"] = args.alias
            if args.type:
                update_data["type"] = args.type
            if args.status:
                update_data["status"] = args.status
        
        if not update_data:
            print("Error: At least one field to update must be specified")
            parser.print_help()
            sys.exit(1)
        
        # Show update summary
        print(f"\nUpdating device {args.device_id} with the following changes:")
        for key, value in update_data.items():
            if key != 'raw_data':
                print(f"  {key}: {value}")
        if 'raw_data' in update_data:
            print("  [raw_data will be updated]")
        
        # Confirm update
        confirm = input("\nDo you want to proceed with this update? (y/n): ")
        if confirm.lower() != 'y':
            print("Update canceled")
            sys.exit(0)
        
        # Perform update
        result = update_device_by_id_cli(args.device_id, update_data)
        
        # Show updated device if requested
        if result and args.show:
            print("\nDevice updated successfully. New values:")
            device = get_device_by_id_cli(args.device_id)
            if device:
                print(f"Serial Number: {device.get('serial_number')}")
                print(f"Plant ID:      {device.get('plant_id')}")
                print(f"Alias:         {device.get('alias')}")
                print(f"Type:          {device.get('type')}")
                print(f"Status:        {device.get('status')}")
                print(f"Last Update:   {device.get('last_update_time')}")
                print(f"Last Updated:  {device.get('last_updated')}")
        
        sys.exit(0 if result else 1)
    elif args.command == "get":
        # Get device by ID
        device = get_device_by_id_cli(args.device_id)
        if device:
            if args.json:
                # Print as JSON
                print(json.dumps(device, default=str, indent=2))
            else:
                # Print in human-readable format
                print("\nDevice Details:")
                print("==============")
                print(f"Serial Number: {device.get('serial_number')}")
                print(f"Plant ID:      {device.get('plant_id')}")
                print(f"Alias:         {device.get('alias')}")
                print(f"Type:          {device.get('type')}")
                print(f"Status:        {device.get('status')}")
                print(f"Last Update:   {device.get('last_update_time')}")
                print(f"Last Updated:  {device.get('last_updated')}")
                if 'raw_data' in device and device['raw_data']:
                    print("\nRaw Data:")
                    try:
                        if isinstance(device['raw_data'], str):
                            raw_data = json.loads(device['raw_data'])
                        else:
                            raw_data = device['raw_data']
                        # Print first 5 key-value pairs
                        count = 0
                        for key, value in raw_data.items():
                            if count < 5:
                                print(f"  {key}: {value}")
                                count += 1
                        if count < len(raw_data):
                            print(f"  ... and {len(raw_data) - count} more items")
                    except:
                        print("  [Unable to parse raw data]")
            sys.exit(0)
        else:
            print(f"Device with ID {args.device_id} not found")
            sys.exit(1)
    elif args.command == "export":
        # Export devices to JSON file
        result = export_devices_to_json(args.output)
        if result:
            print(f"Devices successfully exported to {args.output}")
            sys.exit(0)
        else:
            print(f"Failed to export devices to {args.output}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)