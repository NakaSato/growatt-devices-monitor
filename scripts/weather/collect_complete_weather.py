#!/usr/bin/env python3
"""
Collect Complete Weather Data

This script collects complete weather data from the Growatt API and stores it in the database.
It uses the extended weather_data schema to store all available weather fields.

Usage:
    python collect_complete_weather.py [--plant-id=ID]

Options:
    --plant-id=ID      Specific plant ID to collect weather data for (optional)
    --help, -h         Show this help message
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
import time
import psycopg2
from psycopg2.extras import Json

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app modules
from app.core.growatt import Growatt
from app.config import Config
from app.database import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Collect and store complete weather data')
    parser.add_argument('--plant-id', type=str, help='Specific plant ID to collect weather data for')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show more detailed output')
    parser.add_argument('--dry-run', action='store_true', help='Do not save to database')
    return parser.parse_args()

def get_plants(api):
    """Get all plants or a specific plant if plant_id is provided"""
    try:
        plants = api.get_plants()
        if not plants:
            logger.warning("No plants found")
            return []
        return plants
    except Exception as e:
        logger.error(f"Error getting plants: {str(e)}")
        return []

def save_complete_weather_data(plant_id: str, weather_data: dict) -> bool:
    """
    Save complete weather data to the database.
    
    Args:
        plant_id: Plant ID
        weather_data: Complete weather data dictionary from the API
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not weather_data or 'datas' not in weather_data or not weather_data['datas']:
        logger.warning(f"No weather data available for plant {plant_id}")
        return False
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use the first device data
            device_data = weather_data['datas'][0]
            
            # Current date for the weather data
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Extract fields with proper type conversion
            try:
                temperature = float(device_data.get('envTemp', 0)) if device_data.get('envTemp') else None
            except (ValueError, TypeError):
                temperature = None
                
            try:
                env_humidity = float(device_data.get('envHumidity', 0)) if device_data.get('envHumidity') else None
            except (ValueError, TypeError):
                env_humidity = None
                
            try:
                panel_temp = float(device_data.get('panelTemp', 0)) if device_data.get('panelTemp') else None
            except (ValueError, TypeError):
                panel_temp = None
                
            try:
                wind_speed = float(device_data.get('windSpeed', 0)) if device_data.get('windSpeed') else None
            except (ValueError, TypeError):
                wind_speed = None
                
            try:
                wind_angle = int(device_data.get('windAngle', 0)) if device_data.get('windAngle') else None
            except (ValueError, TypeError):
                wind_angle = None
                
            try:
                irradiation = float(device_data.get('irradiantion', 0)) if device_data.get('irradiantion') else None
            except (ValueError, TypeError):
                irradiation = None
                
            try:
                air_pressure = float(device_data.get('airPressure', 0)) if device_data.get('airPressure') else None
            except (ValueError, TypeError):
                air_pressure = None
                
            try:
                rainfall_intensity = float(device_data.get('rainfallIntensity', 0)) if device_data.get('rainfallIntensity') else None
            except (ValueError, TypeError):
                rainfall_intensity = None
            
            # Create condition text from available data
            condition_parts = []
            if env_humidity is not None:
                condition_parts.append(f"Humidity: {env_humidity}%")
            if wind_speed is not None:
                condition_parts.append(f"Wind: {wind_speed} m/s")
            if wind_angle is not None:
                condition_parts.append(f"Direction: {wind_angle}°")
                
            condition = ", ".join(condition_parts) if condition_parts else None
            
            # Boolean lost status
            lost = device_data.get('lost') == 'true'
            
            # Datalog SN and device status
            datalog_sn = device_data.get('datalogSn')
            device_status = device_data.get('deviceStatus')
            
            # Raw data as JSON
            raw_data = Json(device_data)
            
            # Check if the extended columns exist
            try:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'weather_data' AND column_name = 'env_humidity'
                """)
                has_extended_schema = cursor.fetchone() is not None
            except Exception:
                has_extended_schema = False
            
            if has_extended_schema:
                # Use extended schema
                cursor.execute(
                    """
                    INSERT INTO weather_data
                    (plant_id, date, temperature, condition, env_humidity, panel_temp, 
                     wind_speed, wind_angle, datalog_sn, device_status, lost,
                     irradiation, air_pressure, rainfall_intensity, raw_data, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (plant_id, date) DO UPDATE
                    SET temperature = %s, 
                        condition = %s, 
                        env_humidity = %s, 
                        panel_temp = %s, 
                        wind_speed = %s, 
                        wind_angle = %s, 
                        datalog_sn = %s, 
                        device_status = %s, 
                        lost = %s,
                        irradiation = %s,
                        air_pressure = %s,
                        rainfall_intensity = %s,
                        raw_data = %s,
                        last_updated = NOW()
                    """,
                    (
                        plant_id, today, temperature, condition, env_humidity, panel_temp,
                        wind_speed, wind_angle, datalog_sn, device_status, lost,
                        irradiation, air_pressure, rainfall_intensity, raw_data,
                        # Values for UPDATE
                        temperature, condition, env_humidity, panel_temp,
                        wind_speed, wind_angle, datalog_sn, device_status, lost,
                        irradiation, air_pressure, rainfall_intensity, raw_data
                    )
                )
            else:
                # Use basic schema
                logger.warning("Using basic schema - run scripts/extend_weather_schema.py to enable all fields")
                cursor.execute(
                    """
                    INSERT INTO weather_data
                    (plant_id, date, temperature, condition, last_updated)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (plant_id, date) DO UPDATE
                    SET temperature = %s, condition = %s, last_updated = NOW()
                    """,
                    (plant_id, today, temperature, condition, temperature, condition)
                )
            
            conn.commit()
            
            logger.info(f"Saved complete weather data for plant {plant_id}")
            return True
            
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error saving complete weather data: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving complete weather data: {e}")
        return False

def collect_complete_weather_data(api, plant_id=None, verbose=False, dry_run=False):
    """
    Collect complete weather data for all plants or a specific plant
    
    Args:
        api: Growatt API instance
        plant_id: Optional plant ID to collect data for
        verbose: Whether to show detailed output
        dry_run: If True, don't save to database
        
    Returns:
        int: Number of plants successfully processed
    """
    plants_data = get_plants(api)
    
    # If a specific plant ID is provided, filter the plants list
    if plant_id:
        plants_data = [p for p in plants_data if p.get('id') == plant_id]
        if not plants_data:
            logger.error(f"Plant with ID {plant_id} not found")
            return 0
    
    weather_count = 0
    
    logger.info(f"Processing weather data for {len(plants_data)} plants")
    
    for plant in plants_data:
        plant_id = plant.get('id')
        plant_name = plant.get('plantName', 'Unknown')
        
        try:
            logger.info(f"Collecting weather data for plant: {plant_name} (ID: {plant_id})")
            
            # Get weather data from Growatt API
            weather_data = api.get_weather(plant_id)
            
            if not weather_data:
                logger.warning(f"No weather data available for plant {plant_name}")
                continue
            
            # Pretty print the JSON response in verbose mode
            if verbose:
                logger.info(f"Weather data response for plant {plant_name}:")
                logger.info(json.dumps(weather_data, indent=2))
            
            # Save to database if not in dry run mode
            if not dry_run:
                if save_complete_weather_data(plant_id, weather_data):
                    weather_count += 1
                    logger.info(f"Successfully saved weather data for plant {plant_name}")
                else:
                    logger.warning(f"Failed to save weather data for plant {plant_name}")
            else:
                # In dry run mode, just extract and print the data
                if 'datas' in weather_data and weather_data['datas']:
                    device_data = weather_data['datas'][0]
                    logger.info(f"[DRY RUN] Would save weather data for plant {plant_name}:")
                    logger.info(f"Temperature: {device_data.get('envTemp')}°C")
                    logger.info(f"Humidity: {device_data.get('envHumidity')}%")
                    logger.info(f"Wind Speed: {device_data.get('windSpeed')} m/s")
                    logger.info(f"Wind Angle: {device_data.get('windAngle')}°")
                    logger.info(f"Panel Temperature: {device_data.get('panelTemp')}°C")
                    logger.info(f"Last Update: {device_data.get('lastUpdateTime')}")
                    logger.info(f"Device Status: {device_data.get('deviceStatus')}")
                    weather_count += 1
        except Exception as e:
            logger.error(f"Error collecting weather data for plant {plant_name}: {str(e)}")
    
    return weather_count

def main():
    """Main function to collect complete weather data"""
    args = parse_arguments()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate Growatt credentials
    if not Config.GROWATT_USERNAME or not Config.GROWATT_PASSWORD:
        logger.error("Growatt API credentials not configured")
        sys.exit(1)
    
    # Initialize Growatt API
    logger.info(f"Initializing Growatt API with username: {Config.GROWATT_USERNAME}")
    api = Growatt()
    
    # Try to authenticate
    try:
        logger.info("Logging in to Growatt API...")
        login_success = api.login(Config.GROWATT_USERNAME, Config.GROWATT_PASSWORD)
        if not login_success:
            logger.error("Failed to authenticate with Growatt API")
            sys.exit(1)
        logger.info("Successfully authenticated with Growatt API")
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        sys.exit(1)
    
    # Start time for performance tracking
    start_time = time.time()
    
    # Collect weather data
    mode = "dry run" if args.dry_run else "save"
    logger.info(f"Starting weather data collection ({mode} mode)")
    weather_count = collect_complete_weather_data(
        api, args.plant_id, args.verbose, args.dry_run
    )
    
    # Log results
    elapsed_time = time.time() - start_time
    logger.info(f"Weather data collection completed in {elapsed_time:.2f} seconds")
    logger.info(f"Weather data processed for {weather_count} plants")
    
    # Logout from API
    try:
        logger.info("Logging out from Growatt API...")
        api.logout()
        logger.info("Successfully logged out from Growatt API")
    except Exception as e:
        logger.warning(f"Error during logout: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Weather data collection interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 