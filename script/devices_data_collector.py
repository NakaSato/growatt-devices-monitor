#!/usr/bin/env python3
"""
Device Data Collector

This script fetches device data from the Growatt API and stores it in PostgreSQL.
It's designed to be run as a scheduled task every 15 minutes.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/devices_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("devices_collector")

class DevicesDataCollector:
    """Collects device data from the API and stores it in PostgreSQL"""
    
    def __init__(self):
        """Initialize the collector with configuration from environment variables"""
        self.base_url = "http://localhost:8000"  # Default for local development
        if hasattr(Config, 'API_BASE_URL') and Config.API_BASE_URL:
            self.base_url = Config.API_BASE_URL
        
        # PostgreSQL connection details
        self.pg_host = Config.POSTGRES_HOST
        self.pg_port = Config.POSTGRES_PORT
        self.pg_user = Config.POSTGRES_USER
        self.pg_password = Config.POSTGRES_PASSWORD
        self.pg_db = Config.POSTGRES_DB
        
        self.session = requests.Session()
        self.is_authenticated = False
        
        # Ensure the logs directory exists
        os.makedirs("logs", exist_ok=True)
    
    def connect_to_db(self):
        """Create a connection to the PostgreSQL database"""
        try:
            conn = psycopg2.connect(
                host=self.pg_host,
                port=self.pg_port,
                user=self.pg_user,
                password=self.pg_password,
                dbname=self.pg_db
            )
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def ensure_table_exists(self):
        """Ensure the device_snapshots table exists in the database"""
        conn = None
        try:
            conn = self.connect_to_db()
            cursor = conn.cursor()
            
            # Create the device_snapshots table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_snapshots (
                    id SERIAL PRIMARY KEY,
                    serial_number TEXT NOT NULL,
                    plant_id TEXT,
                    plant_name TEXT,
                    alias TEXT,
                    status TEXT,
                    total_energy TEXT,
                    last_update_time TEXT,
                    raw_data JSONB,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create an index on serial_number and collected_at for faster querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_snapshots_serial
                ON device_snapshots(serial_number)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_snapshots_collected_at
                ON device_snapshots(collected_at)
            """)
            
            conn.commit()
            logger.info("Ensured device_snapshots table exists")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create device_snapshots table: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def authenticate(self):
        """Authenticate with the Growatt API"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/access",
                data={
                    "username": Config.GROWATT_USERNAME,
                    "password": Config.GROWATT_PASSWORD
                }
            )
            
            if response.status_code == 200:
                logger.info("Successfully authenticated with Growatt API")
                self.is_authenticated = True
                return True
            else:
                logger.error(f"Authentication failed with status code {response.status_code}")
                self.is_authenticated = False
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.is_authenticated = False
            return False
    
    def fetch_devices(self):
        """Fetch devices from the API"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/devices",
                headers={"Cache-Control": "no-cache"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch devices: {response.status_code} {response.text}")
                return None
            
            try:
                devices = response.json()
                logger.info(f"Successfully fetched {len(devices)} devices")
                return devices
            except json.JSONDecodeError:
                logger.error("Failed to parse devices response as JSON")
                
                # Try to handle malformed JSON response as seen in the code
                try:
                    text = response.text.strip()
                    if not text.startswith("["):
                        text = "[" + text
                    if not text.endswith("]"):
                        text = text + "]"
                    text = text.replace(",]", "]")
                    
                    devices = json.loads(text)
                    logger.info(f"Successfully parsed {len(devices)} devices with JSON fixing")
                    return devices
                except Exception as parse_error:
                    logger.error(f"Failed to parse devices with fallback method: {parse_error}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching devices: {e}")
            return None
    
    def save_devices_to_db(self, devices):
        """Save devices to the PostgreSQL database"""
        if not devices:
            logger.warning("No devices to save")
            return False
        
        conn = None
        try:
            conn = self.connect_to_db()
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            saved_count = 0
            
            for device in devices:
                try:
                    cursor.execute(
                        """
                        INSERT INTO device_snapshots (
                            serial_number, plant_id, plant_name, alias, 
                            status, total_energy, last_update_time, raw_data, collected_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            device.get('serial_number', ''),
                            device.get('plant_id', ''),
                            device.get('plant_name', ''),
                            device.get('alias', ''),
                            device.get('status', ''),
                            device.get('total_energy', ''),
                            device.get('last_update_time', ''),
                            json.dumps(device),
                            timestamp
                        )
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save device {device.get('serial_number', 'unknown')}: {e}")
            
            conn.commit()
            logger.info(f"Successfully saved {saved_count} devices to PostgreSQL")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save devices to PostgreSQL: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def run(self):
        """Run the collector once"""
        try:
            # Ensure the database table exists
            if not self.ensure_table_exists():
                logger.error("Failed to ensure the database table exists, aborting")
                return False
            
            # Authenticate with the API
            if not self.is_authenticated and not self.authenticate():
                logger.error("Failed to authenticate with API, aborting")
                return False
            
            # Fetch devices
            devices = self.fetch_devices()
            if not devices:
                logger.error("Failed to fetch devices, aborting")
                return False
            
            # Save devices to the database
            if not self.save_devices_to_db(devices):
                logger.error("Failed to save devices to the database")
                return False
            
            logger.info("Successfully completed device data collection")
            return True
        except Exception as e:
            logger.error(f"Unexpected error running collector: {e}")
            return False


def main():
    """Main entry point for the collector"""
    collector = DevicesDataCollector()
    
    try:
        success = collector.run()
        if success:
            logger.info("Device data collection completed successfully")
            sys.exit(0)
        else:
            logger.error("Device data collection failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Device data collection failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()