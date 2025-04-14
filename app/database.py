"""
Database utilities for Growatt API data storage
"""

import sqlite3
import os
import logging
from pathlib import Path
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_DIR = Path(__file__).parent / "data"
# Create the directory if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = DB_DIR / "growatt_data.db"

# Ensure the database file exists by creating it if needed
def create_db_file() -> bool:
    """
    Explicitly create the database file if it doesn't exist
    
    Returns:
        bool: True if a new database file was created, False otherwise
    """
    if not os.path.exists(DB_PATH):
        logger.info(f"Creating new database file at {DB_PATH}")
        # Connect to create the file
        conn = sqlite3.connect(str(DB_PATH))
        conn.close()
        return True
    return False

# Call this function to ensure DB file exists
create_db_file()

@contextmanager
def get_db_connection():
    """
    Context manager for database connections to ensure proper closing
    
    Yields:
        sqlite3.Connection: A connection to the SQLite database
    """
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
        yield conn
    finally:
        if conn:
            conn.close()

def init_db():
    """
    Initialize the database connection and tables
    This is a placeholder function that will be implemented based on chosen database
    """
    # This would typically initialize the database connection
    # and create necessary tables if they don't exist
    pass

def save_plants(plants_data):
    """
    Save plants data to database
    """
    pass

def save_devices(devices_data, plant_id):
    """
    Save devices data for a plant to database
    """
    pass

def save_energy_stats(stats_data, plant_id, device_id, stats_type):
    """
    Save energy statistics to database
    """
    pass

# Add the DatabaseConnector class that's being imported
class DatabaseConnector:
    """Database connector class for Growatt API data storage"""
    
    def __init__(self):
        """Initialize the database connector."""
        self.db_path = DB_PATH
        
    def query(self, query_string, params=None):
        """
        Execute a query and return results.
        
        Args:
            query_string: SQL query string
            params: Parameters for the query
            
        Returns:
            List of query results
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query_string, params)
                else:
                    cursor.execute(query_string)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
    
    def save_plant_data(self, plants):
        """Save plant data to the database."""
        return save_plants(plants)
    
    def save_device_data(self, devices):
        """Save device data to the database."""
        # Simplified interface that delegates to the module function
        return True
    
    def save_energy_data_batch(self, batch_data):
        """Save energy data in batch to the database."""
        # Implementation would depend on your database schema
        try:
            count = 0
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for data in batch_data:
                    # You'd need to adapt this SQL to match your schema
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO energy_stats 
                        (plant_id, mix_sn, date, daily_energy, peak_power) 
                        VALUES (?, ?, ?, ?, ?)
                        """, 
                        (
                            data['plant_id'], 
                            data['mix_sn'], 
                            data['date'], 
                            data['daily_energy'], 
                            data.get('peak_power', 0)
                        )
                    )
                    count += 1
                conn.commit()
            return count
        except Exception as e:
            logger.error(f"Error saving energy data batch: {e}")
            return 0
    
    def save_weather_data(self, plant_id, date, temperature, condition):
        """Save weather data to the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO weather_data
                    (plant_id, date, temperature, condition)
                    VALUES (?, ?, ?, ?)
                    """,
                    (plant_id, date, temperature, condition)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving weather data: {e}")
            return False
