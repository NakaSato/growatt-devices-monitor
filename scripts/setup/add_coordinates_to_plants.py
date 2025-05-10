#!/usr/bin/env python3
"""
Add Coordinates to Plants Table

This script adds latitude and longitude columns to the plants table
in the database, which are needed for weather data collection.

Usage:
    python add_coordinates_to_plants.py [--debug]
"""

import os
import sys
import logging
import argparse

# Add parent directory to path to make app module importable
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import database connector
from app.database import DatabaseConnector
from app.core.growatt import Growatt

def add_coordinates_to_plants():
    """
    Add latitude and longitude columns to the plants table
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize database connector
        db = DatabaseConnector()
        
        # Check if columns already exist
        columns_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'plants' AND 
                  column_name IN ('latitude', 'longitude')
        """
        
        existing_columns = db.query(columns_query)
        existing_column_names = [col['column_name'] for col in existing_columns]
        
        if 'latitude' in existing_column_names and 'longitude' in existing_column_names:
            logger.info("Latitude and longitude columns already exist in plants table")
            return True
            
        # Add columns if they don't exist
        queries = []
        
        if 'latitude' not in existing_column_names:
            queries.append("ALTER TABLE plants ADD COLUMN latitude DOUBLE PRECISION;")
            
        if 'longitude' not in existing_column_names:
            queries.append("ALTER TABLE plants ADD COLUMN longitude DOUBLE PRECISION;")
            
        # Execute queries
        for query in queries:
            db.execute(query)
            logger.info(f"Executed: {query}")
            
        logger.info("Coordinates columns added to plants table successfully")
        
        # Update schema in weather_data table if it exists
        weather_schema_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'weather_data'
        """
        
        weather_table_exists = db.query(weather_schema_query)
        
        if not weather_table_exists:
            # Create weather_data table if it doesn't exist
            create_weather_table_query = """
                CREATE TABLE IF NOT EXISTS weather_data (
                    id SERIAL PRIMARY KEY,
                    plant_id VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    temperature DOUBLE PRECISION,
                    condition VARCHAR(100),
                    data JSONB,
                    last_updated TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT unique_plant_date UNIQUE (plant_id, date)
                );
            """
            
            db.execute(create_weather_table_query)
            logger.info("Created weather_data table")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding coordinates columns: {str(e)}")
        return False

def populate_coordinates_from_growatt():
    """
    Attempt to populate plant coordinates from Growatt API
    
    Returns:
        int: Number of plants updated
    """
    try:
        # Initialize Growatt API
        growatt = Growatt()
        
        # Get API credentials
        from app.config import Config
        username = os.environ.get('GROWATT_USERNAME', Config.GROWATT_USERNAME)
        password = os.environ.get('GROWATT_PASSWORD', Config.GROWATT_PASSWORD)
        
        if not username or not password:
            logger.warning("No Growatt credentials found, skipping coordinate population")
            return 0
            
        # Login to Growatt API
        login_result = growatt.login(username, password)
        if not login_result:
            logger.warning(f"Failed to login to Growatt API, skipping coordinate population")
            return 0
            
        # Try to get plants directly from API endpoints
        plants = []
        endpoints = [
            f"{growatt.BASE_URL}/index/getPlantListTitle",
            f"{growatt.BASE_URL}/panel/getPlantList"
        ]
        
        for endpoint in endpoints:
            try:
                logger.debug(f"Trying plant list endpoint: {endpoint}")
                res = growatt.session.post(endpoint, timeout=30)
                
                # Skip to next endpoint if we get a 404
                if res.status_code == 404:
                    continue
                    
                res.raise_for_status()
                
                response = res.json()
                
                # Check if we got plant data
                if response and isinstance(response, dict) and response.get('result') == 1:
                    if 'data' in response:
                        plants = response['data']
                        logger.debug(f"Successfully retrieved plant list from {endpoint}")
                        break
                    elif 'obj' in response and 'datas' in response['obj']:
                        plants = response['obj']['datas']
                        logger.debug(f"Successfully retrieved plant list from {endpoint} (reformatted)")
                        break
            except Exception as e:
                logger.warning(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
        if not plants:
            logger.warning("No plants found in Growatt API")
            return 0
            
        # Initialize database connector
        db = DatabaseConnector()
        
        # Update plant coordinates in database
        updated_count = 0
        
        for plant in plants:
            # Get plant ID and coordinates
            plant_id = plant.get('id')
            if not plant_id:
                continue
                
            latitude = plant.get('latitude') or plant.get('lat')
            longitude = plant.get('longitude') or plant.get('lng')
            
            if latitude is None or longitude is None:
                continue
                
            try:
                # Convert to float
                latitude = float(latitude)
                longitude = float(longitude)
                
                # Update plant in database
                db.execute(
                    """
                    UPDATE plants
                    SET latitude = %s, longitude = %s
                    WHERE id = %s
                    """,
                    (latitude, longitude, plant_id)
                )
                
                updated_count += 1
                
            except (ValueError, TypeError):
                logger.warning(f"Invalid coordinates for plant {plant_id}: {latitude}, {longitude}")
                continue
                
        logger.info(f"Updated coordinates for {updated_count} plants from Growatt API")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error populating coordinates from Growatt API: {str(e)}")
        return 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Add coordinates columns to plants table')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--skip-populate', action='store_true', help='Skip populating coordinates from Growatt API')
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
    
    # Add coordinates columns
    result = add_coordinates_to_plants()
    
    if result and not args.skip_populate:
        # Populate coordinates from Growatt API
        populate_coordinates_from_growatt()
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main()) 