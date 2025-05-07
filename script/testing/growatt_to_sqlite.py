#!/usr/bin/env python3
"""
Script to save Growatt data to SQLite database

This script creates a basic SQLite database for storing Growatt data
and demonstrates how to interact with it.
"""

import os
import sys
import sqlite3
import json
import logging
import argparse
from datetime import datetime, timedelta
import time

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(parent_dir)

# Import from the Growatt monitoring app
from app.core.growatt import Growatt
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("growatt_sqlite")

# Define the path to the test_jobs.sqlite database
DB_PATH = os.path.join(parent_dir, 'test_jobs.sqlite')

def setup_database():
    """Set up the SQLite database schema for storing Growatt data"""
    logger.info(f"Setting up database at: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create plants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS plants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create devices table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            serial_number TEXT PRIMARY KEY,
            plant_id TEXT NOT NULL,
            alias TEXT,
            type TEXT,
            status TEXT,
            data TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plant_id) REFERENCES plants (id)
        )
        ''')
        
        # Create energy_stats table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS energy_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id TEXT NOT NULL,
            mix_sn TEXT NOT NULL,
            date TEXT NOT NULL,
            daily_energy REAL,
            peak_power REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plant_id) REFERENCES plants (id),
            FOREIGN KEY (mix_sn) REFERENCES devices (serial_number),
            UNIQUE(mix_sn, date)
        )
        ''')
        
        # Create weather_data table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id TEXT NOT NULL,
            date TEXT NOT NULL,
            temperature REAL,
            condition TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plant_id) REFERENCES plants (id),
            UNIQUE(plant_id, date)
        )
        ''')
        
        # Create log table to track collection events
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            collection_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            count INTEGER DEFAULT 0
        )
        ''')
        
        conn.commit()
        logger.info("Database schema created successfully")
        return conn
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        if conn:
            conn.close()
        return None

class GrowattSQLiteCollector:
    """Collects and stores Growatt data in SQLite database"""
    
    def __init__(self, db_conn):
        """Initialize the collector with a database connection"""
        self.conn = db_conn
        self.cursor = db_conn.cursor()
        self.api = Growatt()
        self.plants_count = 0
        self.devices_count = 0
        self.energy_records_count = 0
        self.weather_records_count = 0
    
    def collect_and_store_all_data(self, days_back=7):
        """Main method to collect and store all Growatt data"""
        logger.info("Starting data collection process")
        
        # Log collection start
        self._log_collection_event("full_collection", "started", "Starting full data collection")
        
        try:
            # Authenticate with Growatt API
            logger.info("Authenticating with Growatt API")
            if not self.api.login(Config.GROWATT_USERNAME, Config.GROWATT_PASSWORD):
                logger.error("Failed to authenticate with Growatt API")
                self._log_collection_event("full_collection", "failed", "Authentication failed")
                return False
            
            # Get all plants
            logger.info("Retrieving plants")
            plants_data = self.api.get_plants()
            
            if not plants_data:
                logger.warning("No plants found")
                self._log_collection_event("plants", "empty", "No plants found")
                return False
            
            # Format plants data
            plants = []
            for plant in plants_data:
                plants.append({
                    'id': plant.get('id'),
                    'name': plant.get('plantName', 'Unknown'),
                    'status': 'active'
                })
            
            logger.info(f"Retrieved {len(plants)} plants")
            self._save_plants(plants)
            
            # For each plant, get devices and data
            for plant in plants:
                plant_id = plant.get('id')
                if not plant_id:
                    logger.warning(f"Plant with no ID, skipping: {plant}")
                    continue
                
                logger.info(f"Processing plant {plant.get('name', 'Unknown')} (ID: {plant_id})")
                
                # Try to get devices using get_device_list method instead
                logger.info(f"Retrieving devices for plant {plant_id}")
                
                try:
                    # Using get_device_list method which handles pagination and has better error handling
                    devices_response = self.api.get_device_list(plant_id)
                    
                    # Extract device data
                    if devices_response and devices_response.get('result') == 1 and 'obj' in devices_response:
                        devices_data = devices_response['obj'].get('datas', [])
                        logger.info(f"Retrieved {len(devices_data)} devices for plant {plant_id}")
                        
                        # Format device data for database
                        all_devices = []
                        for device in devices_data:
                            # Get serial number from different possible fields
                            sn = device.get('deviceSn', device.get('sn', device.get('serialNum')))
                            if sn:
                                # Determine device type based on available fields
                                device_type = device.get('deviceType', 'unknown')
                                if 'deviceTypeName' in device:
                                    device_type = device['deviceTypeName'].lower()
                                elif device_type == '1':
                                    device_type = 'inverter'
                                elif device_type == '2':
                                    device_type = 'datalogger'
                                
                                all_devices.append({
                                    'serial_number': sn,
                                    'plant_id': plant_id,
                                    'alias': device.get('deviceAilas', device.get('alias', '')),
                                    'type': device_type,
                                    'status': device.get('status', 'unknown'),
                                    'data': json.dumps(device)
                                })
                        
                        if all_devices:
                            self._save_devices(all_devices)
                            
                            # Try to fetch mix IDs if available
                            try:
                                mix_ids = self.api.get_mix_ids(plant_id)
                                if mix_ids:
                                    logger.info(f"Found {len(mix_ids)} MIX IDs for plant {plant_id}")
                                    
                                    # Process MIX devices
                                    for mix_data in mix_ids:
                                        if len(mix_data) >= 1:
                                            mix_sn = mix_data[0]
                                            logger.info(f"Processing MIX device: {mix_sn}")
                                            
                                            # Collect energy data for the MIX
                                            energy_records = self._collect_mix_energy_data(plant_id, mix_sn, days_back)
                                            if energy_records:
                                                self._save_energy_data(energy_records)
                            except Exception as mix_error:
                                logger.error(f"Error fetching MIX IDs for plant {plant_id}: {mix_error}")
                    else:
                        logger.warning(f"No devices found for plant {plant_id} or invalid response format")
                    
                except Exception as device_error:
                    logger.error(f"Error fetching devices for plant {plant_id}: {device_error}")
                
                # Collect weather data for the plant
                self._collect_weather_data(plant_id)
            
            # Log collection completion
            self._log_collection_event("full_collection", "completed", 
                                     f"Collection completed: {self.plants_count} plants, "
                                     f"{self.devices_count} devices, "
                                     f"{self.energy_records_count} energy records, "
                                     f"{self.weather_records_count} weather records")
            
            logger.info("Data collection process completed successfully")
            logger.info(f"Collected: {self.plants_count} plants, {self.devices_count} devices, "
                      f"{self.energy_records_count} energy records, {self.weather_records_count} weather records")
            return True
            
        except Exception as e:
            logger.error(f"Error in data collection process: {e}", exc_info=True)
            self._log_collection_event("full_collection", "failed", f"Error: {str(e)}")
            return False
    
    def _collect_mix_energy_data(self, plant_id, mix_sn, days_back):
        """Collect energy data for a MIX device"""
        logger.info(f"Collecting energy data for MIX device {mix_sn}")
        
        energy_records = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            logger.info(f"Fetching energy data for {mix_sn} on {date_str}")
            
            try:
                # Get energy data from the API
                energy_data = self.api.get_energy_stats_daily(date_str, plant_id, mix_sn)
                
                if energy_data and energy_data.get('result') == 1 and energy_data.get('obj'):
                    obj_data = energy_data.get('obj', {})
                    daily_energy = obj_data.get('etouser', 0)
                    
                    # Try to extract peak power from charts data
                    peak_power = 0
                    if 'charts' in obj_data and 'ppv' in obj_data['charts']:
                        ppv_data = obj_data['charts']['ppv']
                        if ppv_data and isinstance(ppv_data, list):
                            # Get max value from the ppv chart data
                            ppv_values = [float(val) for val in ppv_data if val and val != '0']
                            if ppv_values:
                                peak_power = max(ppv_values)
                    
                    energy_record = {
                        'plant_id': plant_id,
                        'mix_sn': mix_sn,
                        'date': date_str,
                        'daily_energy': daily_energy,
                        'peak_power': peak_power
                    }
                    energy_records.append(energy_record)
                
                # To avoid overloading the API
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error fetching energy data for {mix_sn} on {date_str}: {e}")
            
            current_date += timedelta(days=1)
        
        return energy_records
    
    def _collect_weather_data(self, plant_id):
        """Collect weather data for a plant"""
        logger.info(f"Collecting weather data for plant {plant_id}")
        try:
            weather_data = self.api.get_weather(plant_id)
            if weather_data and weather_data.get('result') == 1 and weather_data.get('obj'):
                obj_data = weather_data.get('obj', {})
                
                # If the API returns weather data in a different format,
                # we'll need to adapt this extraction logic
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                # Extract temperature and condition from the response
                temperature = None
                condition = None
                
                # Try to find temperature and condition in the response
                if 'weatherTemper' in obj_data:
                    temperature = obj_data.get('weatherTemper')
                elif 'weatherInfo' in obj_data and 'temp' in obj_data['weatherInfo']:
                    temperature = obj_data['weatherInfo'].get('temp')
                
                if 'weatherType' in obj_data:
                    condition = obj_data.get('weatherType')
                elif 'weatherInfo' in obj_data and 'condition' in obj_data['weatherInfo']:
                    condition = obj_data['weatherInfo'].get('condition')
                
                if temperature is not None or condition is not None:
                    weather_record = {
                        'plant_id': plant_id,
                        'date': current_date,
                        'temperature': temperature,
                        'condition': condition
                    }
                    self._save_weather_data([weather_record])
        except Exception as e:
            logger.error(f"Error fetching weather data for plant {plant_id}: {e}")
    
    def _save_plants(self, plants):
        """Save plant data to the database"""
        try:
            for plant in plants:
                plant_id = plant.get('id')
                plant_name = plant.get('name', 'Unknown')
                status = plant.get('status', 'unknown')
                
                if not plant_id:
                    logger.warning(f"Skipping plant with no ID: {plant}")
                    continue
                
                self.cursor.execute('''
                INSERT OR REPLACE INTO plants 
                (id, name, status, last_updated)
                VALUES (?, ?, ?, ?)
                ''', (str(plant_id), plant_name, status, datetime.now()))
                
                self.plants_count += 1
            
            self.conn.commit()
            logger.info(f"Saved {self.plants_count} plants to database")
            self._log_collection_event("plants", "saved", f"Saved {self.plants_count} plants")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving plants to database: {e}")
            self._log_collection_event("plants", "error", f"Error: {str(e)}")
            return False
    
    def _save_devices(self, devices):
        """Save device data to the database"""
        try:
            new_devices = 0
            for device in devices:
                sn = device.get('serial_number')
                
                if not sn:
                    logger.warning(f"Skipping device with no serial number: {device}")
                    continue
                
                self.cursor.execute('''
                INSERT OR REPLACE INTO devices 
                (serial_number, plant_id, alias, type, status, data, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sn,
                    device.get('plant_id'),
                    device.get('alias', ''),
                    device.get('type', 'unknown'),
                    device.get('status', 'unknown'),
                    device.get('data', '{}'),
                    datetime.now()
                ))
                
                new_devices += 1
                self.devices_count += 1
            
            self.conn.commit()
            logger.info(f"Saved {new_devices} devices to database (total: {self.devices_count})")
            self._log_collection_event("devices", "saved", f"Saved {new_devices} devices")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving devices to database: {e}")
            self._log_collection_event("devices", "error", f"Error: {str(e)}")
            return False
    
    def _save_energy_data(self, energy_records):
        """Save energy data to the database"""
        try:
            records_saved = 0
            for record in energy_records:
                self.cursor.execute('''
                INSERT OR REPLACE INTO energy_stats 
                (plant_id, mix_sn, date, daily_energy, peak_power, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    record.get('plant_id'),
                    record.get('mix_sn'),
                    record.get('date'),
                    record.get('daily_energy', 0),
                    record.get('peak_power', 0),
                    datetime.now()
                ))
                
                records_saved += 1
                self.energy_records_count += 1
            
            self.conn.commit()
            logger.info(f"Saved {records_saved} energy records to database (total: {self.energy_records_count})")
            self._log_collection_event("energy", "saved", f"Saved {records_saved} energy records")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving energy data to database: {e}")
            self._log_collection_event("energy", "error", f"Error: {str(e)}")
            return False
    
    def _save_weather_data(self, weather_records):
        """Save weather data to the database"""
        try:
            records_saved = 0
            for record in weather_records:
                self.cursor.execute('''
                INSERT OR REPLACE INTO weather_data 
                (plant_id, date, temperature, condition, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    record.get('plant_id'),
                    record.get('date'),
                    record.get('temperature'),
                    record.get('condition'),
                    datetime.now()
                ))
                
                records_saved += 1
                self.weather_records_count += 1
            
            self.conn.commit()
            logger.info(f"Saved {records_saved} weather records to database (total: {self.weather_records_count})")
            self._log_collection_event("weather", "saved", f"Saved {records_saved} weather records")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving weather data to database: {e}")
            self._log_collection_event("weather", "error", f"Error: {str(e)}")
            return False
    
    def _log_collection_event(self, collection_type, status, message, count=0):
        """Log a collection event to the database"""
        try:
            self.cursor.execute('''
            INSERT INTO collection_logs 
            (timestamp, collection_type, status, message, count)
            VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now(), collection_type, status, message, count))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error logging collection event: {e}")
            return False

def get_db_counts(db_path):
    """Get counts of records in each table in the database"""
    counts = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get a list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            counts[table_name] = count
        
        conn.close()
        
    except sqlite3.Error as e:
        logger.error(f"Error getting database counts: {e}")
    
    return counts

def main():
    """Main function to run the Growatt data collection and storage"""
    parser = argparse.ArgumentParser(description='Collect and store Growatt data in SQLite')
    parser.add_argument('--days', type=int, default=7, help='Number of days of historical data to collect')
    parser.add_argument('--reset', action='store_true', help='Reset the database before collection')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of plants to process (0 for all)')
    
    args = parser.parse_args()
    
    try:
        # If reset is requested, delete the database file
        if args.reset and os.path.exists(DB_PATH):
            logger.warning(f"Deleting existing database at {DB_PATH}")
            os.remove(DB_PATH)
        
        # Set up the database
        conn = setup_database()
        if not conn:
            logger.error("Failed to set up database")
            return 1
        
        # Show initial record counts
        counts_before = get_db_counts(DB_PATH)
        logger.info(f"Initial database record counts: {counts_before}")
        
        # Create collector and run collection
        collector = GrowattSQLiteCollector(conn)
        result = collector.collect_and_store_all_data(days_back=args.days)
        
        # Show final record counts
        counts_after = get_db_counts(DB_PATH)
        logger.info(f"Final database record counts: {counts_after}")
        
        # Calculate and show differences
        diff = {}
        for key in counts_after:
            if key in counts_before:
                diff[key] = counts_after[key] - counts_before[key]
            else:
                diff[key] = counts_after[key]
        
        logger.info(f"Records added during collection: {diff}")
        
        # Close database connection
        conn.close()
        
        if result:
            logger.info("Data collection completed successfully")
            return 0
        else:
            logger.error("Data collection failed")
            return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())