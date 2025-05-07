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
from typing import List, Dict, Any, Optional, Union, Tuple, Generator

import psycopg2
from psycopg2.extras import RealDictCursor
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
                # Start with the configured host
                host = Config.POSTGRES_HOST
                
                # If a direct IP address is provided in config, use it to bypass DNS
                if Config.POSTGRES_IP_ADDRESS:
                    logger.info(f"Using provided IP address {Config.POSTGRES_IP_ADDRESS} instead of hostname {host}")
                    host = Config.POSTGRES_IP_ADDRESS
                else:
                    logger.info(f"Attempting to connect pool to PostgreSQL database at {host} (attempt {retry_count + 1}/{max_retries})")
                    
                    # Try to resolve hostname to IP address
                    try:
                        # Force IPv4 resolution if configured
                        socket_family = socket.AF_INET if Config.POSTGRES_USE_IPV4_ONLY else 0
                        ip_address = socket.getaddrinfo(host, Config.POSTGRES_PORT, family=socket_family, type=socket.SOCK_STREAM)[0][4][0]
                        logger.info(f"Resolved {host} to IP address: {ip_address}")
                        host = ip_address  # Use resolved IP address
                    except socket.gaierror as dns_error:
                        logger.warning(f"Could not resolve hostname {host}: {dns_error}")
                        
                        # If the hostname contains 'supabase', try using preconfigured Supabase pooler IPs
                        if 'supabase' in host.lower() and SUPABASE_POOLER_IPS:
                            # Use the first IP for this attempt, will try others on subsequent retries if needed
                            pooler_ip_index = retry_count % len(SUPABASE_POOLER_IPS)
                            host = SUPABASE_POOLER_IPS[pooler_ip_index]
                            logger.info(f"Trying Supabase pooler IP address: {host}")
                
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
                    # Use plantName first with fallback to name for compatibility
                    plant_name = plant.get('plantName', plant.get('name', ''))
                    
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
