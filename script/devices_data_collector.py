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

# This function will be called by the background service
def run_collection():
    """
    Run the device data collection process.
    This function is designed to be called by the background scheduler.
    
    Returns:
        bool: True if collection was successful, False otherwise
    """
    collector = DevicesDataCollector()
    try:
        success = collector.run()
        if success:
            logger.info("Device data collection completed successfully")
            return True
        else:
            logger.error("Device data collection failed")
            return False
    except Exception as e:
        logger.error(f"Device data collection failed with exception: {e}")
        return False

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
        """Ensure the devices table exists in the database"""
        conn = None
        try:
            conn = self.connect_to_db()
            cursor = conn.cursor()
            
            # Check if table already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'devices'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create the devices table if it doesn't exist
                logger.info("Creating devices table...")
                cursor.execute("""
                    CREATE TABLE devices (
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
                conn.commit()
                logger.info("Devices table created successfully")
            else:
                logger.info("Devices table already exists")
            
            # Verify the table structure to ensure collected_at exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'devices'
            """)
            columns = [col[0] for col in cursor.fetchall()]
            logger.info(f"Found columns in devices table: {columns}")
            
            if 'collected_at' not in columns:
                logger.info("Adding collected_at column to devices table...")
                cursor.execute("""
                    ALTER TABLE devices 
                    ADD COLUMN collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                conn.commit()
                logger.info("Added collected_at column to devices table")
            
            # Now create indexes in a separate transaction
            self.create_indexes(conn)
            
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create devices table: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def create_indexes(self, conn=None):
        """Create indexes on the devices table"""
        close_conn = False
        try:
            if conn is None:
                conn = self.connect_to_db()
                close_conn = True
            
            cursor = conn.cursor()
            
            logger.info("Creating index on serial_number...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_serial
                ON devices(serial_number)
            """)
            
            logger.info("Creating index on collected_at...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_collected_at
                ON devices(collected_at)
            """)
            
            conn.commit()
            logger.info("Indexes on devices table created or already exist")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create indexes: {e}")
            return False
        finally:
            if close_conn and conn:
                conn.close()
    
    def authenticate(self):
        """Authenticate with the Growatt API"""
        try:
            # Clear any existing session cookies and state
            self.session = requests.Session()
            self.is_authenticated = False
            
            response = self.session.post(
                f"{self.base_url}/api/access",
                data={
                    "username": Config.GROWATT_USERNAME,
                    "password": Config.GROWATT_PASSWORD
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30  # Add timeout to prevent hanging requests
            )
            
            # Check for HTTP errors first
            if response.status_code != 200:
                logger.error(f"Authentication failed with status code {response.status_code}: {response.text}")
                return False
            
            # Try to parse the response as JSON
            try:
                result = response.json()
                
                # Check if the response contains any error indicators
                if isinstance(result, dict) and (result.get("status") == "error" or "error" in result):
                    error_msg = result.get("message", "Unknown authentication error")
                    logger.error(f"Authentication error: {error_msg}")
                    return False
                
                logger.info("Successfully authenticated with Growatt API")
                self.is_authenticated = True
                
                # Store the session cookies for later requests
                self.session.cookies.update(response.cookies)
                
                return True
            except json.JSONDecodeError:
                # If we can't parse the response as JSON but got a 200 status code,
                # it might still be successful, so we'll try to continue
                logger.warning(f"Could not parse authentication response as JSON: {response.text[:100]}...")
                self.is_authenticated = True
                return True
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.is_authenticated = False
            return False
    
    def fetch_devices(self):
        """Fetch devices from the API"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Add headers to ensure we get a fresh response
                headers = {
                    "Cache-Control": "no-cache",
                    "Accept": "application/json",
                    "User-Agent": "GrowattMonitor/1.0"
                }
                
                # Directly call the /api/devices endpoint which is implemented in your app
                # This endpoint handles all the plant iteration internally
                devices_response = self.session.get(
                    f"{self.base_url}/api/devices",
                    headers=headers,
                    timeout=60  # Increase timeout as this endpoint aggregates multiple API calls
                )
                
                if devices_response.status_code != 200:
                    logger.error(f"Failed to fetch devices: Status {devices_response.status_code} - {devices_response.text}")
                    
                    # Check if it's an authentication issue
                    if devices_response.status_code in (401, 403) and retry_count < max_retries - 1:
                        logger.warning("Authentication issue detected, trying to re-authenticate...")
                        self.authenticate()
                        retry_count += 1
                        time.sleep(2)
                        continue
                    
                    # For other errors, also try again
                    retry_count += 1
                    time.sleep(2)
                    continue
                
                # Try to parse the response as JSON
                try:
                    devices = devices_response.json()
                    
                    # Validate the response
                    if not devices:
                        logger.warning("Empty devices response")
                        retry_count += 1
                        time.sleep(2)
                        continue
                        
                    if isinstance(devices, dict) and 'status' in devices and devices['status'] == 'error':
                        error_msg = devices.get('message', 'Unknown error')
                        logger.error(f"Error in devices response: {error_msg}")
                        retry_count += 1
                        time.sleep(2)
                        continue
                    
                    # Response should be a list of devices
                    if not isinstance(devices, list):
                        logger.error(f"Unexpected devices response format: {type(devices)}")
                        retry_count += 1
                        time.sleep(2)
                        continue
                    
                    logger.info(f"Successfully fetched {len(devices)} devices")
                    return devices
                    
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse devices response as JSON: {devices_response.text[:200]}...")
                    retry_count += 1
                    time.sleep(2)
                    continue
                
            except requests.exceptions.Timeout:
                logger.error("Timeout when fetching devices")
                retry_count += 1
                time.sleep(2)
                continue
            except Exception as e:
                logger.error(f"Error fetching devices: {e}")
                retry_count += 1
                time.sleep(2)
                continue
        
        logger.error(f"Failed to fetch devices after {max_retries} attempts")
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
            
            # First check if plant_name column exists, add it if not
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'devices'
            """)
            columns = [col[0] for col in cursor.fetchall()]
            
            # Check for missing columns and add them if needed
            missing_columns = []
            required_columns = ['serial_number', 'plant_id', 'plant_name', 'alias', 
                               'status', 'total_energy', 'last_update_time', 'raw_data', 'collected_at']
            
            for col in required_columns:
                if col not in columns:
                    missing_columns.append(col)
            
            # Add missing columns
            for col in missing_columns:
                logger.info(f"Adding missing column '{col}' to devices table")
                if col == 'raw_data':
                    # JSONB type for raw_data
                    cursor.execute(f"ALTER TABLE devices ADD COLUMN {col} JSONB")
                elif col == 'collected_at':
                    # TIMESTAMP with default for collected_at
                    cursor.execute(f"ALTER TABLE devices ADD COLUMN {col} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                else:
                    # TEXT type for other columns
                    cursor.execute(f"ALTER TABLE devices ADD COLUMN {col} TEXT")
            
            # Commit schema changes
            if missing_columns:
                conn.commit()
                logger.info(f"Added missing columns: {', '.join(missing_columns)}")
            
            # Since dropping the constraint didn't work, let's try to work with it
            # First, we check if the 'plants' table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'plants'
                )
            """)
            plants_table_exists = cursor.fetchone()[0]
            
            # If the plants table exists, we'll get the list of valid plant IDs
            valid_plant_ids = []
            if plants_table_exists:
                cursor.execute("SELECT id FROM plants")
                valid_plant_ids = [str(row[0]) for row in cursor.fetchall()]
                logger.info(f"Found {len(valid_plant_ids)} valid plant IDs")
                
                # Insert a fallback plant if we need one and none exists
                if not valid_plant_ids:
                    try:
                        cursor.execute("""
                            INSERT INTO plants (name, latitude, longitude, location, status, capacity) 
                            VALUES ('Fallback Plant', 0, 0, 'Unknown', 'unknown', 0)
                            RETURNING id
                        """)
                        fallback_plant_id = cursor.fetchone()[0]
                        conn.commit()
                        valid_plant_ids = [str(fallback_plant_id)]
                        logger.info(f"Created fallback plant with ID {fallback_plant_id}")
                    except Exception as e:
                        logger.warning(f"Could not create fallback plant: {e}")
                        # Continue anyway - we'll try another approach
            
            # Prepare the data for batch insert
            timestamp = datetime.now().isoformat()
            saved_count = 0
            error_count = 0
            fallback_plant_id = valid_plant_ids[0] if valid_plant_ids else None
            
            for device in devices:
                try:
                    # Get the plant_id or use the fallback
                    plant_id = device.get('plant_id', '')
                    
                    # If plant_id is not in valid_plant_ids and we have a fallback, use the fallback
                    if plants_table_exists and valid_plant_ids and plant_id not in valid_plant_ids:
                        plant_id = fallback_plant_id
                    
                    # Instead of attempting a batch insert which might fail due to constraints,
                    # insert one by one with error handling
                    cursor.execute(
                        """
                        INSERT INTO devices (
                            serial_number, plant_id, plant_name, alias, 
                            status, total_energy, last_update_time, raw_data, collected_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (serial_number) 
                        DO UPDATE SET
                            plant_id = EXCLUDED.plant_id,
                            plant_name = EXCLUDED.plant_name,
                            alias = EXCLUDED.alias,
                            status = EXCLUDED.status,
                            total_energy = EXCLUDED.total_energy,
                            last_update_time = EXCLUDED.last_update_time,
                            raw_data = EXCLUDED.raw_data,
                            collected_at = EXCLUDED.collected_at
                        """,
                        (
                            device.get('serial_number', ''),
                            plant_id,
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
                    
                    # Commit every 10 records to avoid long-running transactions
                    if saved_count % 10 == 0:
                        conn.commit()
                        
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:  # Only log the first few errors
                        logger.error(f"Failed to save device {device.get('serial_number', 'unknown')}: {e}")
                    elif error_count == 6:
                        logger.error("Additional errors omitted...")
            
            # Final commit for any remaining records
            conn.commit()
            
            # If we couldn't save any devices due to constraints, try one more approach:
            # Create a separate snapshot table without constraints
            if saved_count == 0:
                logger.warning("Could not save any devices to the main table, creating device_snapshots table instead")
                
                # Check if device_snapshots table exists, create it if not
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
                
                # Create indexes for the snapshots table
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_serial ON device_snapshots(serial_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_collected_at ON device_snapshots(collected_at)")
                
                conn.commit()
                
                # Now insert the devices into this table
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
                        
                        # Commit every 10 records 
                        if saved_count % 10 == 0:
                            conn.commit()
                    except Exception as e:
                        logger.error(f"Failed to save device to snapshots: {device.get('serial_number', 'unknown')}: {e}")
                
                conn.commit()
                logger.info(f"Saved {saved_count} devices to device_snapshots table")
            else:
                logger.info(f"Successfully saved {saved_count} devices to PostgreSQL (with {error_count} errors)")
            
            return saved_count > 0
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