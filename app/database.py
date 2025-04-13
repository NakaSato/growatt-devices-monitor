import sqlite3
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
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

def init_db() -> bool:
    """
    Initialize the database with required tables if they don't exist
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    logger.info(f"Initializing database at {DB_PATH}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create plants table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT,
                capacity REAL,
                last_updated TIMESTAMP
            )
            ''')
            
            # Create devices table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                sn TEXT PRIMARY KEY,
                plant_id TEXT NOT NULL,
                alias TEXT,
                type TEXT,
                status TEXT,
                last_updated TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id)
            )
            ''')
            
            # Create energy_stats table for daily energy production
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id TEXT NOT NULL,
                mix_sn TEXT NOT NULL,
                date DATE NOT NULL,
                daily_energy REAL NOT NULL,
                peak_power REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id),
                FOREIGN KEY (mix_sn) REFERENCES devices(sn),
                UNIQUE(plant_id, mix_sn, date)
            )
            ''')
            
            # Create weather table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id TEXT NOT NULL,
                date DATE NOT NULL,
                temperature REAL,
                condition TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id),
                UNIQUE(plant_id, date)
            )
            ''')
            
            # Create predictions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id TEXT NOT NULL,
                mix_sn TEXT,
                prediction_date DATE NOT NULL,
                energy_predicted REAL NOT NULL,
                lower_bound REAL,
                upper_bound REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id),
                FOREIGN KEY (mix_sn) REFERENCES devices(sn),
                UNIQUE(plant_id, mix_sn, prediction_date)
            )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_plant_date ON energy_stats(plant_id, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_plant_date ON predictions(plant_id, prediction_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_plant_date ON weather(plant_id, date)')
            
            conn.commit()
            logger.info("Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

class DatabaseConnector:
    """Database connector for the ML module to use"""
    
    def __init__(self):
        """Initialize the database connector"""
        self.db_path = DB_PATH
    
    def query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return results
        
        Args:
            query: SQL query string
            params: Parameters to substitute in the query
            
        Returns:
            List of dictionaries containing the query results
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            return []
    
    def execute(self, query: str, params: Optional[Tuple] = None) -> bool:
        """
        Execute a query without returning results (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query string
            params: Parameters to substitute in the query
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Execute error: {str(e)}")
            return False
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> bool:
        """
        Execute many queries with different parameters
        
        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not params_list:
            return True  # Nothing to do
            
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Execute many error: {str(e)}")
            return False
    
    def save_plant_data(self, plants: List[Dict[str, Any]]) -> bool:
        """
        Save plant data to the database
        
        Args:
            plants: List of plant data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not plants:
            return False
        
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params_list = [
                (
                    plant.get('id'),
                    plant.get('name'),
                    plant.get('location', ''),
                    plant.get('capacity', 0.0),
                    now
                )
                for plant in plants
            ]
            
            return self.execute_many('''
                INSERT OR REPLACE INTO plants (id, name, location, capacity, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', params_list)
        except Exception as e:
            logger.error(f"Save plant data error: {str(e)}")
            return False
    
    def save_device_data(self, devices: List[Dict[str, Any]]) -> bool:
        """
        Save device data to the database
        
        Args:
            devices: List of device data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not devices:
            return False
        
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params_list = [
                (
                    device.get('serial_number'),
                    device.get('plant_id', ''),
                    device.get('alias', ''),
                    device.get('type', ''),
                    device.get('status', ''),
                    now
                )
                for device in devices
            ]
            
            return self.execute_many('''
                INSERT OR REPLACE INTO devices (sn, plant_id, alias, type, status, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', params_list)
        except Exception as e:
            logger.error(f"Save device data error: {str(e)}")
            return False
    
    def save_energy_data(self, plant_id: str, mix_sn: str, date: str, 
                        daily_energy: float, peak_power: Optional[float] = None) -> bool:
        """
        Save daily energy production data
        
        Args:
            plant_id: Plant ID
            mix_sn: Device serial number
            date: Date in ISO format (YYYY-MM-DD)
            daily_energy: Energy produced in kWh
            peak_power: Peak power in kW (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.execute('''
                INSERT OR REPLACE INTO energy_stats (plant_id, mix_sn, date, daily_energy, peak_power)
                VALUES (?, ?, ?, ?, ?)
            ''', (plant_id, mix_sn, date, daily_energy, peak_power))
        except Exception as e:
            logger.error(f"Save energy data error: {str(e)}")
            return False
    
    def save_energy_data_batch(self, energy_data_list: List[Dict[str, Any]]) -> int:
        """
        Save multiple energy data records in a single transaction
        
        Args:
            energy_data_list: List of energy data dictionaries
            
        Returns:
            int: Number of records saved
        """
        if not energy_data_list:
            return 0
            
        try:
            params_list = [
                (
                    record.get('plant_id'),
                    record.get('mix_sn'),
                    record.get('date'),
                    record.get('daily_energy', 0.0),
                    record.get('peak_power')
                )
                for record in energy_data_list
            ]
            
            success = self.execute_many('''
                INSERT OR REPLACE INTO energy_stats (plant_id, mix_sn, date, daily_energy, peak_power)
                VALUES (?, ?, ?, ?, ?)
            ''', params_list)
            
            return len(params_list) if success else 0
        except Exception as e:
            logger.error(f"Batch save energy data error: {str(e)}")
            return 0
    
    def save_weather_data(self, plant_id: str, date: str, temperature: Optional[float], 
                         condition: Optional[str]) -> bool:
        """
        Save weather data for a plant
        
        Args:
            plant_id: Plant ID
            date: Date in ISO format (YYYY-MM-DD)
            temperature: Temperature in degrees
            condition: Weather condition string
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.execute('''
                INSERT OR REPLACE INTO weather (plant_id, date, temperature, condition)
                VALUES (?, ?, ?, ?)
            ''', (plant_id, date, temperature, condition))
        except Exception as e:
            logger.error(f"Save weather data error: {str(e)}")
            return False
            
    def get_latest_energy_date(self, plant_id: str, mix_sn: str) -> Optional[str]:
        """
        Get the latest date for which we have energy data
        
        Args:
            plant_id: Plant ID
            mix_sn: Device serial number
            
        Returns:
            str: Latest date in ISO format (YYYY-MM-DD) or None if no data
        """
        query = '''
        SELECT MAX(date) as latest_date 
        FROM energy_stats 
        WHERE plant_id = ? AND mix_sn = ?
        '''
        
        result = self.query(query, (plant_id, mix_sn))
        if result and result[0]['latest_date']:
            return result[0]['latest_date']
        return None
    
    def save_prediction(self, plant_id: str, mix_sn: Optional[str], prediction_date: str,
                       energy_predicted: float, lower_bound: Optional[float] = None,
                       upper_bound: Optional[float] = None) -> bool:
        """
        Save a prediction to the database
        
        Args:
            plant_id: Plant ID
            mix_sn: Device serial number (optional)
            prediction_date: Date in ISO format (YYYY-MM-DD)
            energy_predicted: Predicted energy production in kWh
            lower_bound: Lower confidence bound (optional)
            upper_bound: Upper confidence bound (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.execute('''
                INSERT OR REPLACE INTO predictions 
                (plant_id, mix_sn, prediction_date, energy_predicted, lower_bound, upper_bound)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (plant_id, mix_sn, prediction_date, energy_predicted, lower_bound, upper_bound))
        except Exception as e:
            logger.error(f"Save prediction error: {str(e)}")
            return False
    
    def save_collection_log(self, stats: Dict[str, Any], success: bool, message: str) -> bool:
        """
        Save data collection log to the database
        
        Args:
            stats: Collection statistics
            success: Whether the collection was successful
            message: Status message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if collection_logs table exists, create if not
            tables = self.query("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_logs'")
            if not tables:
                self.execute('''
                    CREATE TABLE collection_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        message TEXT,
                        plants_count INTEGER,
                        devices_count INTEGER,
                        energy_records_count INTEGER,
                        weather_records_count INTEGER,
                        error_count INTEGER,
                        errors TEXT
                    )
                ''')
            
            # Insert log entry
            return self.execute('''
                INSERT INTO collection_logs (
                    timestamp, success, message, plants_count, devices_count,
                    energy_records_count, weather_records_count, error_count, errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                now,
                1 if success else 0,
                message,
                stats.get('plants', 0),
                stats.get('devices', 0),
                stats.get('energy_stats', 0),
                stats.get('weather', 0),
                len(stats.get('errors', [])),
                '\n'.join(stats.get('errors', []))
            ))
        except Exception as e:
            logger.error(f"Save collection log error: {str(e)}")
            return False
    
    def save_json_data(self, data_type: str, content: str, plant_id: str = None, 
                       device_sn: str = None, source: str = None) -> bool:
        """
        Save raw JSON data to the database for archival and analysis
        
        Args:
            data_type: Type of data (plants, devices, energy, weather, etc.)
            content: JSON content as string
            plant_id: Optional plant ID
            device_sn: Optional device serial number
            source: Optional source identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if json_data table exists, create if not
            tables = self.query("SELECT name FROM sqlite_master WHERE type='table' AND name='json_data'")
            if not tables:
                self.execute('''
                    CREATE TABLE json_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        data_type TEXT NOT NULL,
                        plant_id TEXT,
                        device_sn TEXT,
                        source TEXT,
                        content TEXT NOT NULL
                    )
                ''')
            
            # Insert JSON data
            return self.execute('''
                INSERT INTO json_data (timestamp, data_type, plant_id, device_sn, source, content)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (now, data_type, plant_id, device_sn, source, content))
        except Exception as e:
            logger.error(f"Save JSON data error: {str(e)}")
            return False
