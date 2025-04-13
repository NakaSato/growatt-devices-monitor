import sqlite3
import os
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_DIR = Path(__file__).parent / "data"
# Create the directory if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = DB_DIR / "growatt_data.db"

# Ensure the database file exists by creating it if needed
def create_db_file():
    """Explicitly create the database file if it doesn't exist"""
    if not os.path.exists(DB_PATH):
        logger.info(f"Creating new database file at {DB_PATH}")
        # Connect to create the file
        conn = sqlite3.connect(str(DB_PATH))
        conn.close()
        return True
    return False

# Call this function to ensure DB file exists
create_db_file()

def init_db():
    """Initialize the database with required tables if they don't exist"""
    logger.info(f"Initializing database at {DB_PATH}")
    
    conn = get_db_connection()
    try:
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
        
        conn.commit()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def get_db_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
    return conn

class DatabaseConnector:
    """Database connector for the ML module to use"""
    
    def __init__(self):
        """Initialize the database connector"""
        self.db_path = DB_PATH
    
    def query(self, query, params=None):
        """Execute a query and return results"""
        conn = get_db_connection()
        try:
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
        finally:
            conn.close()
    
    def execute(self, query, params=None):
        """Execute a query without returning results (INSERT, UPDATE, DELETE)"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Execute error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def execute_many(self, query, params_list):
        """Execute many queries with different parameters"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Execute many error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_plant_data(self, plants):
        """Save plant data to the database"""
        if not plants:
            return False
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for plant in plants:
                cursor.execute('''
                INSERT OR REPLACE INTO plants (id, name, location, capacity, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    plant.get('id'),
                    plant.get('name'),
                    plant.get('location', ''),
                    plant.get('capacity', 0.0),
                    now
                ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save plant data error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_device_data(self, devices):
        """Save device data to the database"""
        if not devices:
            return False
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for device in devices:
                cursor.execute('''
                INSERT OR REPLACE INTO devices (sn, plant_id, alias, type, status, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    device.get('serial_number'),
                    device.get('plant_id', ''),
                    device.get('alias', ''),
                    device.get('type', ''),
                    device.get('status', ''),
                    now
                ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save device data error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_energy_data(self, plant_id, mix_sn, date, daily_energy, peak_power=None):
        """Save daily energy production data"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO energy_stats (plant_id, mix_sn, date, daily_energy, peak_power)
            VALUES (?, ?, ?, ?, ?)
            ''', (plant_id, mix_sn, date, daily_energy, peak_power))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save energy data error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_energy_data_batch(self, energy_data_list):
        """Save multiple energy data records in a single transaction"""
        if not energy_data_list:
            return 0
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            records_saved = 0
            
            for record in energy_data_list:
                cursor.execute('''
                INSERT OR REPLACE INTO energy_stats (plant_id, mix_sn, date, daily_energy, peak_power)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    record.get('plant_id'),
                    record.get('mix_sn'),
                    record.get('date'),
                    record.get('daily_energy', 0.0),
                    record.get('peak_power')
                ))
                records_saved += 1
            
            conn.commit()
            return records_saved
        except Exception as e:
            logger.error(f"Batch save energy data error: {str(e)}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def save_weather_data(self, plant_id, date, temperature, condition):
        """Save weather data for a plant"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO weather (plant_id, date, temperature, condition)
            VALUES (?, ?, ?, ?)
            ''', (plant_id, date, temperature, condition))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save weather data error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def get_latest_energy_date(self, plant_id, mix_sn):
        """Get the latest date for which we have energy data"""
        query = '''
        SELECT MAX(date) as latest_date 
        FROM energy_stats 
        WHERE plant_id = ? AND mix_sn = ?
        '''
        
        result = self.query(query, (plant_id, mix_sn))
        if result and result[0]['latest_date']:
            return result[0]['latest_date']
        return None
    
    def save_prediction(self, plant_id, mix_sn, prediction_date, energy_predicted, lower_bound=None, upper_bound=None):
        """Save a prediction to the database"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO predictions 
            (plant_id, mix_sn, prediction_date, energy_predicted, lower_bound, upper_bound)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (plant_id, mix_sn, prediction_date, energy_predicted, lower_bound, upper_bound))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save prediction error: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
