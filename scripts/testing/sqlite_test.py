#!/usr/bin/env python3
"""
SQLite Database Job Test Script

This script demonstrates how to save data to the test_jobs.sqlite database.
It shows how to create tables, insert data, and query the database.
"""

import os
import sys
import sqlite3
import json
import logging
import argparse
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sqlite_test")

# Define the path to the test_jobs.sqlite database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test_jobs.sqlite')

def connect_to_db():
    """Connect to the SQLite database"""
    logger.info(f"Connecting to SQLite database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        logger.info("Successfully connected to the database")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        sys.exit(1)

def create_tables(conn):
    """Create necessary tables if they don't exist"""
    cursor = conn.cursor()
    
    # Create a jobs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        data TEXT
    )
    ''')
    
    # Create a devices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_sn TEXT UNIQUE NOT NULL,
        plant_id INTEGER NOT NULL,
        device_type TEXT NOT NULL,
        status TEXT NOT NULL,
        last_update TIMESTAMP NOT NULL,
        data TEXT
    )
    ''')
    
    # Create a plants table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        capacity REAL,
        last_update TIMESTAMP NOT NULL,
        data TEXT
    )
    ''')
    
    conn.commit()
    logger.info("Tables created successfully")

def insert_sample_data(conn):
    """Insert sample data into the database"""
    cursor = conn.cursor()
    now = datetime.now()
    
    # Sample job data
    job_types = ['collect_devices', 'collect_plants', 'collect_energy', 'send_notifications']
    statuses = ['pending', 'running', 'completed', 'failed']
    
    # Insert sample jobs
    for i in range(5):
        job_type = random.choice(job_types)
        status = random.choice(statuses)
        created_at = now - timedelta(hours=random.randint(1, 24))
        updated_at = created_at + timedelta(minutes=random.randint(5, 60))
        
        data = {
            'parameters': {
                'days_back': random.randint(1, 7),
                'include_weather': random.choice([True, False])
            },
            'result': {
                'success': status == 'completed',
                'message': f"Job {job_type} {'completed successfully' if status == 'completed' else 'failed'}"
            }
        }
        
        cursor.execute('''
        INSERT INTO jobs (job_type, status, created_at, updated_at, data)
        VALUES (?, ?, ?, ?, ?)
        ''', (job_type, status, created_at, updated_at, json.dumps(data)))
    
    # Sample plant data
    plant_names = ['Solar Farm A', 'Rooftop Solar B', 'Home Installation C', 'Commercial Solar D', 'Industrial Solar E']
    locations = ['Bangkok', 'Chiang Mai', 'Phuket', 'Pattaya', 'Khon Kaen']
    
    for i in range(5):
        plant_id = 10000000 + i
        name = plant_names[i]
        location = locations[i]
        capacity = random.uniform(5.0, 100.0)
        last_update = now - timedelta(hours=random.randint(1, 12))
        
        data = {
            'latitude': random.uniform(12.0, 20.0),
            'longitude': random.uniform(98.0, 105.0),
            'created_date': (now - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
            'total_energy': random.uniform(1000, 50000),
            'today_energy': random.uniform(5, 50)
        }
        
        cursor.execute('''
        INSERT INTO plants (id, name, location, capacity, last_update, data)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (plant_id, name, location, capacity, last_update, json.dumps(data)))
    
    # Sample device data
    device_types = ['inverter', 'datalogger', 'battery', 'smart meter']
    device_statuses = ['online', 'offline', 'warning', 'error']
    
    for i in range(20):
        device_sn = f"GW{random.randint(10000, 99999)}"
        plant_id = 10000000 + random.randint(0, 4)
        device_type = random.choice(device_types)
        status = random.choice(device_statuses)
        last_update = now - timedelta(minutes=random.randint(5, 240))
        
        data = {
            'model': f"Growatt-{random.randint(1, 5)}000-{random.choice(['S', 'M', 'L'])}",
            'firmware': f"V1.{random.randint(0, 9)}.{random.randint(0, 9)}",
            'parameters': {
                'temperature': random.uniform(25, 45),
                'efficiency': random.uniform(85, 98),
                'power': random.uniform(100, 5000)
            }
        }
        
        try:
            cursor.execute('''
            INSERT INTO devices (device_sn, plant_id, device_type, status, last_update, data)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (device_sn, plant_id, device_type, status, last_update, json.dumps(data)))
        except sqlite3.IntegrityError:
            # If device_sn already exists, update instead
            cursor.execute('''
            UPDATE devices 
            SET plant_id = ?, device_type = ?, status = ?, last_update = ?, data = ?
            WHERE device_sn = ?
            ''', (plant_id, device_type, status, last_update, json.dumps(data), device_sn))
    
    conn.commit()
    logger.info("Sample data inserted successfully")

def query_data(conn):
    """Query and display data from the database"""
    cursor = conn.cursor()
    
    # Query jobs
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 5")
    jobs = cursor.fetchall()
    logger.info(f"Retrieved {len(jobs)} jobs")
    for job in jobs:
        logger.info(f"Job ID: {job['id']}, Type: {job['job_type']}, Status: {job['status']}, Created: {job['created_at']}")
    
    # Query plants
    cursor.execute("SELECT * FROM plants ORDER BY last_update DESC LIMIT 5")
    plants = cursor.fetchall()
    logger.info(f"Retrieved {len(plants)} plants")
    for plant in plants:
        logger.info(f"Plant ID: {plant['id']}, Name: {plant['name']}, Location: {plant['location']}, Capacity: {plant['capacity']} kW")
    
    # Query devices
    cursor.execute("SELECT * FROM devices ORDER BY last_update DESC LIMIT 10")
    devices = cursor.fetchall()
    logger.info(f"Retrieved {len(devices)} devices")
    for device in devices:
        logger.info(f"Device SN: {device['device_sn']}, Type: {device['device_type']}, Status: {device['status']}, Plant ID: {device['plant_id']}")
    
    # Query devices by status
    cursor.execute("SELECT status, COUNT(*) as count FROM devices GROUP BY status")
    status_counts = cursor.fetchall()
    logger.info("Device status counts:")
    for status in status_counts:
        logger.info(f"  {status['status']}: {status['count']} devices")

def main():
    """Main function to run the SQLite test"""
    parser = argparse.ArgumentParser(description='Test SQLite database operations')
    parser.add_argument('--create-only', action='store_true', help='Only create tables, don\'t insert sample data')
    parser.add_argument('--reset', action='store_true', help='Drop and recreate all tables')
    
    args = parser.parse_args()
    
    # Connect to the database
    conn = connect_to_db()
    
    try:
        if args.reset:
            # Drop all tables if reset is requested
            logger.warning("Dropping all existing tables...")
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS jobs")
            cursor.execute("DROP TABLE IF EXISTS devices")
            cursor.execute("DROP TABLE IF EXISTS plants")
            conn.commit()
            logger.info("All tables dropped successfully")
        
        # Create tables
        create_tables(conn)
        
        if not args.create_only:
            # Insert sample data
            insert_sample_data(conn)
            
            # Query and display data
            query_data(conn)
        
        logger.info("SQLite database test completed successfully")
        return 0
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return 1
    
    finally:
        # Close the connection
        if conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    sys.exit(main())