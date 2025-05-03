"""
Database utilities for Growatt API data storage

This module provides database connection and operations for storing and retrieving
Growatt solar panel monitoring data using PostgreSQL.
"""

import os
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple, Generator

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """
    Context manager for database connections to ensure proper closing
    
    Yields:
        Connection: A connection to the PostgreSQL database
    """
    conn = None
    try:
        # Use environment variables or config for connection parameters
        conn = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            dbname=Config.POSTGRES_DB
        )
        # Enable dictionary-like row access
        conn.cursor_factory = RealDictCursor
        yield conn
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        with get_db_connection() as conn:
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
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plant_id) REFERENCES plants (id)
                )
            ''')
            
            # Create energy_stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS energy_stats (
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    plant_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    temperature REAL,
                    condition TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plant_id) REFERENCES plants (id),
                    UNIQUE(plant_id, date)
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_date ON energy_stats(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_mix_sn ON energy_stats(mix_sn)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_plant_id ON devices(plant_id)')
            
            conn.commit()
            logger.info("Database tables initialized successfully for PostgreSQL database")
            return True
            
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error initializing database: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {e}")
        return False

# Initialize database tables when module is loaded
init_db()

# Add the DatabaseConnector class that's being imported
class DatabaseConnector:
    """Database connector class for Growatt API data storage"""
    
    def __init__(self):
        """Initialize the database connector."""
        pass
        
    def query(self, query_string: str, params: Optional[Union[Tuple, Dict[str, Any], List[Any]]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return results.
        
        Args:
            query_string: SQL query string
            params: Parameters for the query (tuple, dict, or list)
            
        Returns:
            List of query results as dictionary-like objects
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query_string, params)
                else:
                    cursor.execute(query_string)
                
                # PostgreSQL returns a list of dictionaries already
                results = cursor.fetchall()
                return [dict(row) for row in results]
                    
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected query error: {e}")
            return []
    
    def save_plant_data(self, plants: List[Dict[str, Any]]) -> bool:
        """
        Save plant data to the database.
        
        Args:
            plants: List of plant data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                for plant in plants:
                    plant_id = plant.get('id')
                    plant_name = plant.get('name', '')
                    
                    if not plant_id:
                        logger.warning(f"Skipping plant with no ID: {plant}")
                        continue
                    
                    cursor.execute(
                        """
                        INSERT INTO plants
                        (id, name, status, last_updated)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (id) DO UPDATE
                        SET name = %s, status = %s, last_updated = NOW()
                        """,
                        (
                            plant_id, 
                            plant_name, 
                            plant.get('status', 'unknown'),
                            plant_name,
                            plant.get('status', 'unknown')
                        )
                    )
                conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving plants: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving plants: {e}")
            return False
    
    def save_device_data(self, devices: List[Dict[str, Any]]) -> bool:
        """
        Save device data to the database.
        
        Args:
            devices: List of device data dictionaries with keys:
                     serial_number, plant_id, alias, type, status
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for device in devices:
                    sn = device.get('serial_number')
                    plant_id = device.get('plant_id')
                    
                    if not sn or not plant_id:
                        logger.warning(f"Skipping device with missing serial number or plant_id: {device}")
                        continue
                    
                    cursor.execute(
                        """
                        INSERT INTO devices
                        (serial_number, plant_id, alias, type, status, last_updated)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (serial_number) DO UPDATE
                        SET plant_id = %s, alias = %s, type = %s, status = %s, last_updated = NOW()
                        """,
                        (
                            sn,
                            plant_id,
                            device.get('alias', ''),
                            device.get('type', 'unknown'),
                            device.get('status', 'unknown'),
                            plant_id,
                            device.get('alias', ''),
                            device.get('type', 'unknown'),
                            device.get('status', 'unknown')
                        )
                    )
                conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving devices: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving devices: {e}")
            return False
    
    def save_energy_data_batch(self, batch_data: List[Dict[str, Any]]) -> int:
        """
        Save energy data in batch to the database.
        
        Args:
            batch_data: List of energy data dictionaries with keys:
                        plant_id, mix_sn, date, daily_energy, peak_power
                        
        Returns:
            int: Number of records successfully saved
        """
        try:
            count = 0
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for data in batch_data:
                    # Validate required fields
                    if not all(key in data for key in ['plant_id', 'mix_sn', 'date', 'daily_energy']):
                        logger.warning(f"Skipping energy data with missing required fields: {data}")
                        continue
                    
                    cursor.execute(
                        """
                        INSERT INTO energy_stats 
                        (plant_id, mix_sn, date, daily_energy, peak_power, last_updated) 
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (mix_sn, date) DO UPDATE
                        SET daily_energy = %s, peak_power = %s, last_updated = NOW()
                        """, 
                        (
                            data['plant_id'], 
                            data['mix_sn'], 
                            data['date'], 
                            data['daily_energy'], 
                            data.get('peak_power', 0),
                            data['daily_energy'],
                            data.get('peak_power', 0)
                        )
                    )
                    count += 1
                conn.commit()
            return count
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving energy data batch: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error saving energy data batch: {e}")
            return 0
    
    def save_weather_data(self, plant_id: str, date: str, temperature: Optional[float], condition: Optional[str]) -> bool:
        """
        Save weather data to the database.
        
        Args:
            plant_id: Plant ID
            date: Date string in YYYY-MM-DD format
            temperature: Temperature value (can be None)
            condition: Weather condition description (can be None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT INTO weather_data
                    (plant_id, date, temperature, condition, last_updated)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (plant_id, date) DO UPDATE
                    SET temperature = %s, condition = %s, last_updated = NOW()
                    """,
                    (plant_id, date, temperature, condition, temperature, condition)
                )
                conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving weather data: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving weather data: {e}")
            return False
