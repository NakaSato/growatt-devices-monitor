#!/usr/bin/env python3
"""
Plant Data Collector

This script fetches plant data from the Growatt API and stores it in PostgreSQL.
It's designed to be run as a scheduled task once daily.
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
        logging.FileHandler("logs/plants_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("plants_collector")

# This function will be called by the background service
def run_collection():
    """
    Run the plant data collection process.
    This function is designed to be called by the background scheduler.
    
    Returns:
        bool: True if collection was successful, False otherwise
    """
    collector = PlantsDataCollector()
    try:
        success = collector.run()
        if success:
            logger.info("Plant data collection completed successfully")
            return True
        else:
            logger.error("Plant data collection failed")
            return False
    except Exception as e:
        logger.error(f"Plant data collection failed with exception: {e}")
        return False

class PlantsDataCollector:
    """Collects plant data from the API and stores it in PostgreSQL"""
    
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
        """Ensure the plants table exists in the database"""
        conn = None
        try:
            conn = self.connect_to_db()
            cursor = conn.cursor()
            
            # Create the plants table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT,
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    capacity DOUBLE PRECISION,
                    current_output DOUBLE PRECISION,
                    today_energy DOUBLE PRECISION,
                    peak_output DOUBLE PRECISION,
                    total_energy DOUBLE PRECISION,
                    install_date TEXT,
                    location TEXT,
                    timezone TEXT,
                    plant_type TEXT,
                    co2_avoided DOUBLE PRECISION,
                    city TEXT,
                    country TEXT,
                    raw_data JSONB,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for faster querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_plants_status
                ON plants(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_plants_location
                ON plants(location)
            """)
            
            conn.commit()
            logger.info("Ensured plants table exists")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create plants table: {e}")
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
    
    def fetch_plants(self):
        """Fetch plants from the API"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/plants",
                headers={"Cache-Control": "no-cache"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch plants: {response.status_code} {response.text}")
                return None
            
            try:
                plants = response.json()
                logger.info(f"Successfully fetched {len(plants)} plants")
                return plants
            except json.JSONDecodeError:
                logger.error("Failed to parse plants response as JSON")
                
                # Try to handle malformed JSON response if needed
                try:
                    text = response.text.strip()
                    if not text.startswith("["):
                        text = "[" + text
                    if not text.endswith("]"):
                        text = text + "]"
                    text = text.replace(",]", "]")
                    
                    plants = json.loads(text)
                    logger.info(f"Successfully parsed {len(plants)} plants with JSON fixing")
                    return plants
                except Exception as parse_error:
                    logger.error(f"Failed to parse plants with fallback method: {parse_error}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching plants: {e}")
            return None
    
    def save_plants_to_db(self, plants):
        """Save plants to the PostgreSQL database"""
        if not plants:
            logger.warning("No plants to save")
            return False
        
        conn = None
        try:
            conn = self.connect_to_db()
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            saved_count = 0
            
            for plant in plants:
                try:
                    # Convert status codes to text if needed
                    status = plant.get('status', 'unknown')
                    if status == '1':
                        status = 'active'
                    elif status == '2':
                        status = 'warning'
                    elif status == '3':
                        status = 'error'
                    elif status == '0':
                        status = 'offline'
                    
                    # Handle different field names in API response
                    plant_id = plant.get('id', '')
                    plant_name = plant.get('name', '') or plant.get('plantName', '')
                    lat = plant.get('latitude', None) or plant.get('lat', None)
                    lng = plant.get('longitude', None) or plant.get('lng', None)
                    
                    cursor.execute(
                        """
                        INSERT INTO plants (
                            id, name, status, latitude, longitude, capacity, 
                            current_output, today_energy, peak_output, total_energy,
                            install_date, location, timezone, plant_type, co2_avoided,
                            city, country, raw_data, last_updated
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            status = EXCLUDED.status,
                            latitude = EXCLUDED.latitude,
                            longitude = EXCLUDED.longitude,
                            capacity = EXCLUDED.capacity,
                            current_output = EXCLUDED.current_output,
                            today_energy = EXCLUDED.today_energy,
                            peak_output = EXCLUDED.peak_output,
                            total_energy = EXCLUDED.total_energy,
                            install_date = EXCLUDED.install_date,
                            location = EXCLUDED.location,
                            timezone = EXCLUDED.timezone,
                            plant_type = EXCLUDED.plant_type,
                            co2_avoided = EXCLUDED.co2_avoided,
                            city = EXCLUDED.city,
                            country = EXCLUDED.country,
                            raw_data = EXCLUDED.raw_data,
                            last_updated = EXCLUDED.last_updated
                        """,
                        (
                            plant_id,
                            plant_name,
                            status,
                            float(lat) if lat else None,
                            float(lng) if lng else None,
                            float(plant.get('capacity', 0)) or float(plant.get('nominalPower', 0)),
                            float(plant.get('current_output', 0)) or float(plant.get('currentPower', 0)),
                            float(plant.get('today_energy', 0)) or float(plant.get('eToday', 0)),
                            float(plant.get('peak_output', 0)) or float(plant.get('peakPower', 0)),
                            float(plant.get('total_energy', 0)) or float(plant.get('eTotal', 0)),
                            plant.get('install_date') or plant.get('creatDate'),
                            plant.get('location') or f"{plant.get('city', '')}, {plant.get('country', '')}".strip(', '),
                            plant.get('timezone'),
                            plant.get('plantType'),
                            float(plant.get('co2', 0)),
                            plant.get('city'),
                            plant.get('country'),
                            json.dumps(plant),
                            timestamp
                        )
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save plant {plant.get('id', 'unknown')}: {e}")
            
            conn.commit()
            logger.info(f"Successfully saved {saved_count} plants to PostgreSQL")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save plants to PostgreSQL: {e}")
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
            
            # Fetch plants
            plants = self.fetch_plants()
            if not plants:
                logger.error("Failed to fetch plants, aborting")
                return False
            
            # Save plants to the database
            if not self.save_plants_to_db(plants):
                logger.error("Failed to save plants to the database")
                return False
            
            logger.info("Successfully completed plant data collection")
            return True
        except Exception as e:
            logger.error(f"Unexpected error running collector: {e}")
            return False

def main():
    """Main entry point for the collector"""
    collector = PlantsDataCollector()
    
    try:
        success = collector.run()
        if success:
            logger.info("Plant data collection completed successfully")
            sys.exit(0)
        else:
            logger.error("Plant data collection failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Plant data collection failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()