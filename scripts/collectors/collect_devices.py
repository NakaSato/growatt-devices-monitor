#!/usr/bin/env python3
"""
Collect Devices Script

A simple script to collect device data from the Growatt API and store it in a local JSON file.
This script doesn't depend on the Flask app or database.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Add the project root directory to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Import common utilities from scripts package
from app.config import Config
from scripts.utils.utils import (
    ensure_dir,
    save_to_json,
    retry_with_backoff,
    create_common_parser,
    make_api_request
)

# Configure logging
# Ensure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

logger = logging.getLogger("collect_devices")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(logs_dir, 'collect_devices.log'))
    ]
)

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
        self.base_url = Config.GROWATT_BASE_URL
        self.username = Config.GROWATT_USERNAME
        self.password = Config.GROWATT_PASSWORD
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
            
        auth_data = {
            "username": self.username,
            "password": self.password
        }
            
        response = make_api_request(
            url=f"{self.base_url}/api/access",
            method="POST",
            data=auth_data
        )
        
        if response.get("success", False):
            auth_result = response
            if auth_result.get("status") == "success":
                self.is_authenticated = True
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed with status: {auth_result.get('status')}")
        else:
            logger.error(f"Authentication failed: {response.get('error')}")
                
        return False
    
    @retry_with_backoff
    def fetch_devices(self) -> list:
        """
        Fetch devices from the API
        
        Returns:
            list: List of device data dictionaries
        """
        response = make_api_request(
            url=f"{self.base_url}/api/devices",
            method="GET"
        )
        
        if response.get("success", False):
            devices = response.get("data", []) if isinstance(response.get("data"), list) else response
            
            if not devices and isinstance(devices, list):
                logger.warning("No devices returned from the API")
            elif not isinstance(devices, list):
                logger.error(f"Unexpected response format: {type(devices)}")
                devices = []
            else:
                logger.info(f"Successfully fetched {len(devices)} devices")
            
            return devices
        else:
            logger.error(f"Error fetching devices: {response.get('error')}")
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
        
        return save_to_json(devices, output_file)
    
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
                    return True
                else:
                    logger.error("Failed to save devices to file")
                    return False
            else:
                logger.warning("No devices to save, collection process completed with no errors")
                return True
        except Exception as e:
            logger.error(f"Error during device data collection: {str(e)}")
            return False

def main():
    """Main function"""
    # Create parser with common arguments
    parser = create_common_parser()
    parser.description = "Collect device data from Growatt API"
    parser.add_argument("--output", dest="output_file", help="Output JSON file path")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Ensure output directory exists
    output_dir = ensure_dir(args.output_dir)
    
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