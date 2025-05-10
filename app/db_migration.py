"""
Database migration utility to add missing columns to existing tables
"""
import logging
from app.database import get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_raw_data_column():
    """
    Add the raw_data JSONB column to the devices table if it doesn't exist
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'devices' AND column_name = 'raw_data'
            """)
            
            if not cursor.fetchone():
                logger.info("Adding raw_data column to devices table...")
                cursor.execute("ALTER TABLE devices ADD COLUMN raw_data JSONB")
                conn.commit()
                logger.info("Successfully added raw_data column to devices table")
            else:
                logger.info("raw_data column already exists in devices table")
            
            return True
            
    except Exception as e:
        logger.error(f"Error adding raw_data column to devices table: {e}")
        return False

def add_device_data_table():
    """
    Add the device_data table if it doesn't exist
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if the table exists
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'device_data'
            """)
            
            if not cursor.fetchone():
                logger.info("Creating device_data table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS device_data (
                        id SERIAL PRIMARY KEY,
                        device_serial_number TEXT NOT NULL,
                        energy_today REAL,
                        energy_total REAL,
                        ac_power REAL,
                        collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        raw_data JSONB,
                        FOREIGN KEY (device_serial_number) REFERENCES devices (serial_number)
                    )
                """)
                
                # Create indexes for faster queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_data_sn ON device_data(device_serial_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_data_collected_at ON device_data(collected_at)')
                
                conn.commit()
                logger.info("Successfully created device_data table")
            else:
                logger.info("device_data table already exists")
            
            return True
            
    except Exception as e:
        logger.error(f"Error creating device_data table: {e}")
        return False

def run_migrations():
    """
    Run all database migrations
    
    Returns:
        bool: True if successful, False if an error occurred
    """
    try:
        logger.info("Running database migrations...")
        add_raw_data_column()
        add_device_data_table()
        logger.info("Database migrations completed")
        return True
    except Exception as e:
        logger.error(f"Database migration error: {e}")
        return False

if __name__ == "__main__":
    run_migrations()
