"""
Database utilities for Growatt API data storage

This module provides database connection and operations for storing and retrieving
Growatt solar panel monitoring data using PostgreSQL.
"""

import os
import logging
import time
import socket
from pathlib import Path
from contextlib import contextmanager
import json
from typing import List, Dict, Any, Optional, Union, Tuple, Generator
from datetime import datetime, timedelta, date
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import pool

from app.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase pooler IP addresses - used if DNS resolution fails
SUPABASE_POOLER_IPS = [
    "52.74.252.201",
    "52.77.146.31", 
    "54.255.219.82"
]

# Global connection pool
_connection_pool = None

def get_connection_pool():
    """
    Creates or returns the global connection pool
    
    Returns:
        ThreadedConnectionPool: Connection pool for PostgreSQL
    """
    global _connection_pool
    
    if _connection_pool is None:
        max_retries = Config.POSTGRES_MAX_RETRIES
        retry_count = 0
        retry_delay = Config.POSTGRES_RETRY_DELAY  # Initial delay in seconds
        
        # Set a reasonable socket timeout to avoid hanging
        socket.setdefaulttimeout(Config.POSTGRES_CONNECT_TIMEOUT)
        
        min_connections = int(os.getenv('POSTGRES_MIN_CONNECTIONS', '1'))
        max_connections = int(os.getenv('POSTGRES_MAX_CONNECTIONS', '10'))
        
        while retry_count < max_retries:
            try:
                host = resolve_host()
                logger.info(f"Creating connection pool to {host}:{Config.POSTGRES_PORT} as {Config.POSTGRES_USER}")
                _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=min_connections,
                    maxconn=max_connections,
                    host=host,
                    port=Config.POSTGRES_PORT,
                    user=Config.POSTGRES_USER,
                    password=Config.POSTGRES_PASSWORD,
                    dbname=Config.POSTGRES_DB,
                    connect_timeout=Config.POSTGRES_CONNECT_TIMEOUT
                )
                
                logger.info(f"Successfully created PostgreSQL connection pool with {min_connections}-{max_connections} connections")
                break
            except psycopg2.OperationalError as e:
                retry_count += 1
                if "could not translate host name" in str(e) or "could not connect to server" in str(e):
                    logger.warning(f"Connection pool attempt {retry_count}/{max_retries} failed: {e}")
                    if retry_count < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"PostgreSQL connection pool error after {max_retries} attempts: {e}")
                        logger.info("If you're experiencing DNS resolution issues, please check:")
                        logger.info("1. Internet connectivity")
                        logger.info("2. DNS configuration")
                        logger.info("3. Try using direct IP address by setting POSTGRES_IP_ADDRESS in your .env file")
                        logger.info("4. For macOS, you might need to flush DNS cache with 'sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder'")
                        logger.info("5. For local development, consider using localhost or Docker")
                        logger.info("6. If using Supabase, connect via the pooler URL: aws-0-ap-southeast-1.pooler.supabase.com")
                        raise
                else:
                    # For other operational errors, don't retry
                    logger.error(f"PostgreSQL connection pool error: {e}")
                    raise
            except psycopg2.Error as e:
                logger.error(f"PostgreSQL connection pool error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected connection pool error: {e}")
                raise
                
    return _connection_pool

def resolve_host():
    """
    Resolves the PostgreSQL host from configuration or environment.
    
    Returns:
        str: Resolved host (IP address or hostname)
    """
    host = Config.POSTGRES_HOST
    
    # If a direct IP address is provided in config, use it to bypass DNS
    if Config.POSTGRES_IP_ADDRESS:
        logger.info(f"Using provided IP address {Config.POSTGRES_IP_ADDRESS} instead of hostname {host}")
        return Config.POSTGRES_IP_ADDRESS
    
    logger.info(f"Attempting to resolve hostname {host}")
    
    # Try to resolve hostname to IP address
    try:
        # Force IPv4 resolution if configured
        socket_family = socket.AF_INET if Config.POSTGRES_USE_IPV4_ONLY else 0
        ip_address = socket.getaddrinfo(host, Config.POSTGRES_PORT, family=socket_family, type=socket.SOCK_STREAM)[0][4][0]
        logger.info(f"Resolved {host} to IP address: {ip_address}")
        return ip_address
    except socket.gaierror as dns_error:
        logger.warning(f"Could not resolve hostname {host}: {dns_error}")
        
        # If the hostname contains 'supabase', try using preconfigured Supabase pooler IPs
        if 'supabase' in host.lower() and SUPABASE_POOLER_IPS:
            # Use the first IP for this attempt, will try others on subsequent retries if needed
            pooler_ip_index = retry_count % len(SUPABASE_POOLER_IPS)
            host = SUPABASE_POOLER_IPS[pooler_ip_index]
            logger.info(f"Trying Supabase pooler IP address: {host}")
            return host
        raise

@contextmanager
def get_db_connection():
    """
    Context manager for database connections to ensure proper closing
    Uses connection pool in transaction mode
    
    Yields:
        Connection: A connection to the PostgreSQL database
    """
    pool = get_connection_pool()
    conn = None
    
    try:
        # Get connection from pool
        conn = pool.getconn()
        
        # Set transaction mode (autocommit=False is the default)
        conn.autocommit = False
        
        # Enable dictionary-like row access
        conn.cursor_factory = RealDictCursor
        
        yield conn
        
        # Commit the transaction if no exception occurred
        conn.commit()
    except Exception as e:
        # Rollback in case of error
        if conn:
            try:
                conn.rollback()
                logger.info("Transaction rolled back due to error")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        raise
    finally:
        # Return connection to pool
        if conn:
            try:
                pool.putconn(conn)
            except Exception as put_error:
                logger.error(f"Error returning connection to pool: {put_error}")
                # In case of failure to return to pool, try to close it directly
                try:
                    conn.close()
                except:
                    pass

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
                    last_update_time TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_data JSONB,
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
            
            # Create files table for storing files
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT,
                    content BYTEA NOT NULL,
                    plant_id TEXT,
                    device_id TEXT,
                    size_bytes INTEGER,
                    md5_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB,
                    FOREIGN KEY (plant_id) REFERENCES plants (id),
                    FOREIGN KEY (device_id) REFERENCES devices (serial_number),
                    UNIQUE(file_path)
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_date ON energy_stats(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_mix_sn ON energy_stats(mix_sn)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_plant_id ON devices(plant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_plant_id ON files(plant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_device_id ON files(device_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename)')
            
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

# Import and run database migrations to add missing columns
try:
    from app.db_migration import run_migrations
    # Run migrations to ensure all required columns exist
    run_migrations()
except ImportError:
    logger.warning("db_migration module not found, skipping migrations")
except Exception as e:
    logger.error(f"Error running database migrations: {e}")

# Add the DatabaseConnector class that's being imported
class DatabaseConnector:
    """Database connector class for Growatt API data storage"""
    
    def __init__(self):
        """Initialize the database connector."""
        pass
        
    def execute(self, query_string: str, params: Optional[Union[Tuple, Dict[str, Any], List[Any]]] = None) -> bool:
        """
        Execute a SQL statement without expecting results (for INSERT, UPDATE, CREATE, etc.).
        
        Args:
            query_string: SQL query string
            params: Parameters for the query (tuple, dict, or list)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query_string, params)
                else:
                    cursor.execute(query_string)
                return True
                    
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL execute error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected execute error: {e}")
            return False

    def _prepare_device_data(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare device data for database insertion/update.
        
        Args:
            device: Raw device data dictionary
            
        Returns:
            Dict containing prepared device data with standardized fields
        """
        if not device.get('serial_number'):
            logger.warning(f"Skipping device with no serial number: {device}")
            return {}
        
        # Handle last_update_time field - could be string or datetime
        if isinstance(device.get('last_update_time'), str):
            try:
                # Convert to datetime object if it's a string
                device['last_update_time'] = datetime.strptime(device['last_update_time'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # If parsing fails, use current datetime
                logger.warning(f"Invalid date format for last_update_time: {device['last_update_time']}")
                device['last_update_time'] = datetime.now()
        
        # Prepare raw_data as JSON if present
        raw_data = Json(device.get('raw_data', {})) if device.get('raw_data') else Json({})
        
        return {
            'serial_number': device['serial_number'],
            'plant_id': device['plant_id'],
            'alias': device.get('alias', ''),
            'type': device.get('type', ''),
            'status': device.get('status', 'unknown'),
            'last_update_time': device['last_update_time'],
            'raw_data': raw_data
        }

    def _check_raw_data_column(self, cursor) -> bool:
        """
        Check if raw_data column exists in the devices table.
        
        Args:
            cursor: Database cursor
            
        Returns:
            bool: True if raw_data column exists, False otherwise
        """
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'devices' AND column_name = 'raw_data'
            """)
            return cursor.fetchone() is not None
        except Exception:
            # If we can't check, assume it doesn't exist
            return False

    def _save_device_to_db(self, cursor, device_data: Dict[str, Any], raw_data_column_exists: bool) -> None:
        """
        Save a single device to the database.
        
        Args:
            cursor: Database cursor
            device_data: Prepared device data dictionary
            raw_data_column_exists: Whether raw_data column exists in the table
        """
        # Check if the device already exists
        cursor.execute(
            """
            SELECT serial_number FROM devices 
            WHERE serial_number = %s
            """,
            (device_data['serial_number'],)
        )
        exists = cursor.fetchone()
        
        if exists:
            if raw_data_column_exists:
                # Update existing device with raw_data
                cursor.execute(
                    """
                    UPDATE devices 
                    SET plant_id = %s,
                        alias = %s,
                        type = %s,
                        status = %s,
                        last_update_time = %s,
                        last_updated = NOW(),
                        raw_data = %s
                    WHERE serial_number = %s
                    """,
                    (
                        device_data['plant_id'],
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time'],
                        device_data['raw_data'],
                        device_data['serial_number']
                    )
                )
            else:
                # Update existing device without raw_data
                cursor.execute(
                    """
                    UPDATE devices 
                    SET plant_id = %s,
                        alias = %s,
                        type = %s,
                        status = %s,
                        last_update_time = %s,
                        last_updated = NOW()
                    WHERE serial_number = %s
                    """,
                    (
                        device_data['plant_id'],
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time'],
                        device_data['serial_number']
                    )
                )
        else:
            if raw_data_column_exists:
                # Insert new device with raw_data
                cursor.execute(
                    """
                    INSERT INTO devices 
                    (serial_number, plant_id, alias, type, status, last_update_time, last_updated, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                    """,
                    (
                        device_data['serial_number'],
                        device_data['plant_id'],
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time'],
                        device_data['raw_data']
                    )
                )
            else:
                # Insert new device without raw_data
                cursor.execute(
                    """
                    INSERT INTO devices 
                    (serial_number, plant_id, alias, type, status, last_update_time, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        device_data['serial_number'],
                        device_data['plant_id'],
                        device_data['alias'],
                        device_data['type'],
                        device_data['status'],
                        device_data['last_update_time']
                    )
                )

    def save_device_data(self, devices_data: List[Dict[str, Any]]) -> bool:
        """
        Save device data to the database.
        This is used by the data collector to save device data retrieved from the Growatt API.
        
        Args:
            devices_data: List of device data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if raw_data column exists once for all devices
                raw_data_column_exists = self._check_raw_data_column(cursor)
                
                for device in devices_data:
                    # Prepare device data
                    device_data = self._prepare_device_data(device)
                    if not device_data:
                        continue
                    
                    # Save device to database
                    self._save_device_to_db(cursor, device_data, raw_data_column_exists)
                
                conn.commit()
                return True
            
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving device data: {e}")
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving device data: {e}")
            if conn:
                conn.rollback()
            return False

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
                    # Use plantName first with fallback to name for compatibility
                    plant_name = plant.get('plantName', plant.get('name', ''))
                    
                    if not plant_id:
                        logger.warning(f"Skipping plant with no ID: {plant}")
                        continue
                    
                    # Convert last_update_time to datetime if it's a string
                    if isinstance(plant.get('last_update_time'), str):
                        try:
                            plant['last_update_time'] = datetime.strptime(plant['last_update_time'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            logger.warning(f"Invalid date format for plant {plant_id}: {plant['last_update_time']}")
                            plant['last_update_time'] = datetime.now()
                    
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
    
    def save_devices(self, devices_data: List[Dict[str, Any]]) -> bool:
        """
        Save devices data to the database
        """
        if not devices_data:
            return True
        
        logger = logging.getLogger(__name__)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for device in devices_data:
                # Ensure we have all required fields
                if not all(k in device for k in ['serial_number', 'plant_id', 'alias', 'type', 'status']):
                    logger.warning(f"Device data missing required fields: {device}")
                    continue
                
                # Convert the last_update_time string to a proper datetime object if it's a string
                if 'last_update_time' in device and isinstance(device['last_update_time'], str):
                    try:
                        # Try to parse the date string in format "YYYY-MM-DD HH:MM:SS"
                        device['last_update_time'] = datetime.strptime(device['last_update_time'], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # If parsing fails, use current datetime
                        logger.warning(f"Invalid date format for last_update_time: {device['last_update_time']}")
                        device['last_update_time'] = datetime.now()
                
                # Prepare raw_data as JSON
                raw_data = json.dumps(device.get('raw_data', {}))
                
                # Check if raw_data column exists in the table
                try:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'devices' AND column_name = 'raw_data'
                    """)
                    raw_data_column_exists = cursor.fetchone() is not None
                except Exception:
                    # If we can't check, assume it doesn't exist
                    raw_data_column_exists = False
                
                # Check if the device already exists
                cursor.execute(
                    """
                    SELECT serial_number FROM devices 
                    WHERE serial_number = %s
                    """,
                    (device['serial_number'],)
                )
                exists = cursor.fetchone()
                
                if exists:
                    if raw_data_column_exists:
                        # Update existing device with raw_data
                        cursor.execute(
                            """
                            UPDATE devices 
                            SET plant_id = %s,
                                alias = %s,
                                type = %s,
                                status = %s,
                                last_update_time = %s,
                                last_updated = NOW(),
                                raw_data = %s
                            WHERE serial_number = %s
                            """,
                            (
                                device['plant_id'],
                                device['alias'],
                                device['type'],
                                device['status'],
                                device['last_update_time'],
                                raw_data,
                                device['serial_number']
                            )
                        )
                    else:
                        # Update existing device without raw_data
                        cursor.execute(
                            """
                            UPDATE devices 
                            SET plant_id = %s,
                                alias = %s,
                                type = %s,
                                status = %s,
                                last_update_time = %s,
                                last_updated = NOW()
                            WHERE serial_number = %s
                            """,
                            (
                                device['plant_id'],
                                device['alias'],
                                device['type'],
                                device['status'],
                                device['last_update_time'],
                                device['serial_number']
                            )
                        )
                else:
                    if raw_data_column_exists:
                        # Insert new device with raw_data
                        cursor.execute(
                            """
                            INSERT INTO devices 
                            (serial_number, plant_id, alias, type, status, last_update_time, last_updated, raw_data)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                            """,
                            (
                                device['serial_number'],
                                device['plant_id'],
                                device['alias'],
                                device['type'],
                                device['status'],
                                device['last_update_time'],
                                raw_data
                            )
                        )
                    else:
                        # Insert new device without raw_data
                        cursor.execute(
                            """
                            INSERT INTO devices 
                            (serial_number, plant_id, alias, type, status, last_update_time, last_updated)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """,
                            (
                                device['serial_number'],
                                device['plant_id'],
                                device['alias'],
                                device['type'],
                                device['status'],
                                device['last_update_time']
                            )
                        )
            
            conn.commit()
            return True
        
        except Exception as e:
            logger.error(f"Unexpected error saving devices: {e}")
            if conn:
                conn.rollback()
                logger.info("Transaction rolled back due to error")
            
            # Log the first device data for debugging
            if devices_data:
                logger.error(f"Failed to save device data: {json.dumps(devices_data, default=str, indent=2)}")
            
            return False
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

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
                    
                    # Convert date to datetime if it's a string
                    if isinstance(data.get('date'), str):
                        try:
                            data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
                        except ValueError:
                            logger.warning(f"Invalid date format for energy data: {data['date']}")
                            data['date'] = datetime.now().date()
                    
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
                
                # Convert date to datetime if it's a string
                if isinstance(date, str):
                    try:
                        date = datetime.strptime(date, '%Y-%m-%d').date()
                    except ValueError:
                        logger.warning(f"Invalid date format for weather data: {date}")
                        date = datetime.now().date()
                
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
    
    def save_file_to_db(self, 
                        filename: str, 
                        file_path: str, 
                        content: bytes, 
                        file_type: Optional[str] = None, 
                        plant_id: Optional[str] = None, 
                        device_id: Optional[str] = None, 
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a file to the database as binary data.
        
        Args:
            filename: Original filename
            file_path: Path of the file (used as a unique identifier)
            content: Binary content of the file
            file_type: MIME type or extension of the file
            plant_id: Associated plant ID (optional)
            device_id: Associated device ID (optional)
            metadata: Additional metadata as a JSON dictionary (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import hashlib
            
            # Calculate MD5 hash for file integrity
            md5_hash = hashlib.md5(content).hexdigest()
            size_bytes = len(content)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT INTO files
                    (filename, file_path, file_type, content, plant_id, device_id, 
                     size_bytes, md5_hash, created_at, last_updated, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
                    ON CONFLICT (file_path) DO UPDATE
                    SET content = %s, 
                        file_type = %s,
                        plant_id = %s,
                        device_id = %s,
                        size_bytes = %s,
                        md5_hash = %s,
                        last_updated = NOW(),
                        metadata = %s
                    """,
                    (
                        filename, 
                        file_path, 
                        file_type, 
                        psycopg2.Binary(content), 
                        plant_id, 
                        device_id, 
                        size_bytes, 
                        md5_hash,
                        psycopg2.extras.Json(metadata) if metadata else None,
                        # Values for the ON CONFLICT UPDATE
                        psycopg2.Binary(content),
                        file_type,
                        plant_id,
                        device_id,
                        size_bytes,
                        md5_hash,
                        psycopg2.extras.Json(metadata) if metadata else None
                    )
                )
                conn.commit()
                
            logger.info(f"Successfully saved file to database: {file_path} ({size_bytes} bytes)")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving file: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving file: {e}")
            return False
    
    def get_file_from_db(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file from the database by its path.
        
        Args:
            file_path: Path of the file to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with file information and content, or None if not found
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT id, filename, file_path, file_type, content, plant_id, device_id, 
                           size_bytes, md5_hash, created_at, last_updated, metadata
                    FROM files
                    WHERE file_path = %s
                    """,
                    (file_path,)
                )
                
                result = cursor.fetchone()
                
                if result:
                    # Convert to regular dict and ensure content is bytes
                    file_info = dict(result)
                    
                    # psycopg2 returns memoryview, convert to bytes
                    if isinstance(file_info.get('content'), memoryview):
                        file_info['content'] = bytes(file_info['content'])
                        
                    # Calculate MD5 to verify integrity
                    import hashlib
                    md5_hash = hashlib.md5(file_info['content']).hexdigest()
                    if md5_hash != file_info.get('md5_hash'):
                        logger.warning(f"MD5 hash mismatch for file {file_path}. Stored: {file_info.get('md5_hash')}, Calculated: {md5_hash}")
                    
                    return file_info
                else:
                    logger.info(f"File not found in database: {file_path}")
                    return None
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error retrieving file: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving file: {e}")
            return None
    
    def file_exists_in_db(self, file_path: str) -> bool:
        """
        Check if a file exists in the database.
        
        Args:
            file_path: Path of the file to check
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT 1 FROM files WHERE file_path = %s LIMIT 1
                    """,
                    (file_path,)
                )
                
                return cursor.fetchone() is not None
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error checking file existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence: {e}")
            return False
    
    def list_files_in_db(self, 
                         plant_id: Optional[str] = None, 
                         device_id: Optional[str] = None, 
                         file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files in the database with optional filtering.
        
        Args:
            plant_id: Filter by plant ID (optional)
            device_id: Filter by device ID (optional)
            file_type: Filter by file type (optional)
            
        Returns:
            List[Dict[str, Any]]: List of file information dictionaries (without content)
        """
        try:
            query = """
                SELECT id, filename, file_path, file_type, plant_id, device_id, 
                       size_bytes, md5_hash, created_at, last_updated, metadata
                FROM files
                WHERE 1=1
            """
            
            params = []
            
            if plant_id:
                query += " AND plant_id = %s"
                params.append(plant_id)
                
            if device_id:
                query += " AND device_id = %s"
                params.append(device_id)
                
            if file_type:
                query += " AND file_type = %s"
                params.append(file_type)
                
            query += " ORDER BY created_at DESC"
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, tuple(params))
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error listing files: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}")
            return []
    
    def delete_file_from_db(self, file_path: str) -> bool:
        """
        Delete a file from the database.
        
        Args:
            file_path: Path of the file to delete
            
        Returns:
            bool: True if the file was deleted, False otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    DELETE FROM files WHERE file_path = %s
                    """,
                    (file_path,)
                )
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted file from database: {file_path}")
                else:
                    logger.info(f"File not found for deletion: {file_path}")
                
                return deleted
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error deleting file: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {e}")
            return False
