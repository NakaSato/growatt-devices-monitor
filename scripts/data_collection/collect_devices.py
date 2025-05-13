#!/usr/bin/env python3
"""
Collect Devices Script

A simple script to collect device data from the Growatt API and store it in a local JSON file.
This script doesn't depend on the Flask app or database.
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
from datetime import datetime

from app.config import Config

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
    parser = argparse.ArgumentParser(description="Collect device data from Growatt API")
    parser.add_argument("--server", dest="server_url", default="https://monitoring.boring9.dev", 
                      help="URL of the server running the Growatt monitor")
    parser.add_argument("--username", dest="username", help="Growatt API username")
    parser.add_argument("--password", dest="password", help="Growatt API password")
    parser.add_argument("--output", dest="output_file", help="Output JSON file path")
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