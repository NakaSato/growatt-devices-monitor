#!/usr/bin/env python3
"""
Weather Data Collector for Growatt Plants

This script collects weather data for all Growatt plants and stores it in the database.
It can be run separately from the main data collector to update weather data at different intervals.

Usage:
    python weather_collector.py [--plant-id=ID]

Options:
    --plant-id=ID      Specific plant ID to collect weather data for (optional)
    --help, -h         Show this help message
    --debug            Print raw API responses for debugging

Environment variables:
    GROWATT_USERNAME        Growatt API username
    GROWATT_PASSWORD        Growatt API password
    WEATHER_API_KEY         Weather API key (optional, uses Growatt's weather data if not provided)
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
import time
import json

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import app modules
from app.core.growatt import Growatt
from app.database import DatabaseConnector, get_db_connection
from app.config import Config
try:
    from psycopg2.extras import Json
except ImportError:
    # If psycopg2.extras is not available, define a simple Json class
    class Json:
        def __init__(self, data):
            self.data = data

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Collect weather data for Growatt plants')
    parser.add_argument('--plant-id', type=str, help='Specific plant ID to collect weather data for')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--debug', action='store_true', help='Debug mode - print raw API responses')
    
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

def has_extended_weather_schema():
    """Check if the database has the extended weather schema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'weather_data' AND column_name = 'env_humidity'
            """)
            return cursor.fetchone() is not None
    except Exception as e:
        logger.warning(f"Error checking for extended weather schema: {e}")
        return False

def save_weather_data_extended(plant_id, date, temperature, 
                             humidity=None, wind_speed=None, wind_angle=None, 
                             panel_temp=None, device_status=None, lost=None,
                             raw_data=None):
    """
    Save weather data using the extended schema.
    
    Args:
        plant_id: Plant ID
        date: Date in YYYY-MM-DD format
        temperature: Temperature value
        humidity: Humidity percentage
        wind_speed: Wind speed in m/s
        wind_angle: Wind direction in degrees
        panel_temp: Panel temperature
        device_status: Device status
        lost: Whether the device is offline
        raw_data: Raw data as a JSON object
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Generate a condition string for backward compatibility
            condition_parts = []
            if humidity is not None:
                condition_parts.append(f"Humidity: {humidity}%")
            if wind_speed is not None:
                condition_parts.append(f"Wind: {wind_speed} m/s")
            if wind_angle is not None:
                condition_parts.append(f"Direction: {wind_angle}°")
                
            condition = ", ".join(condition_parts) if condition_parts else None
            
            cursor.execute(
                """
                INSERT INTO weather_data
                (plant_id, date, temperature, condition, env_humidity, panel_temp, 
                 wind_speed, wind_angle, device_status, lost,
                 raw_data, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (plant_id, date) DO UPDATE
                SET temperature = %s, 
                    condition = %s, 
                    env_humidity = %s, 
                    panel_temp = %s, 
                    wind_speed = %s, 
                    wind_angle = %s, 
                    device_status = %s, 
                    lost = %s,
                    raw_data = %s,
                    last_updated = NOW()
                """,
                (
                    plant_id, date, temperature, condition, humidity, panel_temp,
                    wind_speed, wind_angle, device_status, lost, raw_data,
                    # Values for UPDATE
                    temperature, condition, humidity, panel_temp,
                    wind_speed, wind_angle, device_status, lost, raw_data
                )
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving extended weather data: {e}")
        return False

def collect_weather_data(api, plant_id=None, debug=False):
    """Collect weather data for all plants or a specific plant"""
    db = DatabaseConnector()
    plants_data = get_plants(api)
    
    # Check if extended schema is available
    use_extended_schema = has_extended_weather_schema()
    if use_extended_schema:
        logger.info("Using extended weather schema")
    else:
        logger.info("Using basic weather schema - run extend_weather_schema.py to enable all fields")
    
    # If a specific plant ID is provided, filter the plants list
    if plant_id:
        plants_data = [p for p in plants_data if p.get('id') == plant_id]
        if not plants_data:
            logger.error(f"Plant with ID {plant_id} not found")
            return False
    
    weather_count = 0
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Limit to a small number of plants if in debug mode
    if debug and len(plants_data) > 2:
        logger.info(f"Debug mode: limiting to first 2 plants out of {len(plants_data)}")
        plants_data = plants_data[:2]
    
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
            
            # In debug mode, print the raw weather data response
            if debug:
                logger.info(f"Raw weather data response for plant {plant_name}:")
                logger.info(json.dumps(weather_data, indent=2))
            
            # Extract weather metrics from data
            temperature = None
            humidity = None
            wind_speed = None
            wind_angle = None
            panel_temp = None
            device_status = None
            lost = None
            
            # Extract device data from the API response based on format
            device_data = None
            if 'datas' in weather_data and weather_data['datas']:
                # Direct response format - get first non-lost device
                for device in weather_data['datas']:
                    if device.get('lost') != "true":
                        device_data = device
                        break
                
                # If all devices are lost, use the first one
                if device_data is None and weather_data['datas']:
                    device_data = weather_data['datas'][0]
            elif 'obj' in weather_data and 'datas' in weather_data['obj'] and weather_data['obj']['datas']:
                # Response nested under 'obj' - get first non-lost device
                obj_data = weather_data['obj']
                for device in obj_data['datas']:
                    if device.get('lost') != "true":
                        device_data = device
                        break
                
                # If all devices are lost, use the first one
                if device_data is None and obj_data['datas']:
                    device_data = obj_data['datas'][0]
            
            # Extract weather metrics if we have device data
            if device_data:
                # Extract environmental temperature
                try:
                    temperature = float(device_data.get('envTemp', 0)) if device_data.get('envTemp') else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid temperature value: {device_data.get('envTemp')}")
                
                # Extract humidity
                try:
                    humidity = float(device_data.get('envHumidity', 0)) if device_data.get('envHumidity') else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid humidity value: {device_data.get('envHumidity')}")
                
                # Extract wind speed
                try:
                    wind_speed = float(device_data.get('windSpeed', 0)) if device_data.get('windSpeed') else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid wind speed value: {device_data.get('windSpeed')}")
                
                # Extract wind angle
                try:
                    wind_angle = int(device_data.get('windAngle', 0)) if device_data.get('windAngle') else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid wind angle value: {device_data.get('windAngle')}")
                
                # Extract panel temperature
                try:
                    panel_temp = float(device_data.get('panelTemp', 0)) if device_data.get('panelTemp') else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid panel temperature value: {device_data.get('panelTemp')}")
                
                # Extract device status
                device_status = device_data.get('deviceStatus')
                
                # Extract lost status
                lost = device_data.get('lost') == "true"
            
            # Save to database only if we have valid temperature data
            if temperature is not None:
                # Log the data we're about to save
                info_parts = [f"Temperature: {temperature}°C"]
                if humidity is not None:
                    info_parts.append(f"Humidity: {humidity}%")
                if wind_speed is not None:
                    info_parts.append(f"Wind: {wind_speed} m/s")
                if wind_angle is not None:
                    info_parts.append(f"Direction: {wind_angle}°")
                if panel_temp is not None:
                    info_parts.append(f"Panel Temp: {panel_temp}°C")
                
                logger.info(f"Weather for {plant_name}: {', '.join(info_parts)}")
                
                # Store in database - use extended schema if available
                if use_extended_schema:
                    # Use extended schema to store all fields
                    try:
                        raw_data = Json(device_data) if device_data else None
                    except Exception:
                        # If Json conversion fails, store as None
                        raw_data = None
                    
                    success = save_weather_data_extended(
                        plant_id=plant_id,
                        date=today,
                        temperature=temperature,
                        humidity=humidity,
                        wind_speed=wind_speed,
                        wind_angle=wind_angle,
                        panel_temp=panel_temp,
                        device_status=device_status,
                        lost=lost,
                        raw_data=raw_data
                    )
                else:
                    # Use basic schema with condition field for backwards compatibility
                    condition_parts = []
                    if humidity is not None:
                        condition_parts.append(f"Humidity: {humidity}%")
                    if wind_speed is not None:
                        condition_parts.append(f"Wind: {wind_speed} m/s")
                    
                    condition = ", ".join(condition_parts) if condition_parts else None
                    
                    success = db.save_weather_data(
                        plant_id=plant_id,
                        date=today,
                        temperature=temperature,
                        condition=condition
                    )
                
                if success:
                    weather_count += 1
                    logger.info(f"Successfully saved weather data for plant {plant_name}")
                else:
                    logger.warning(f"Failed to save weather data for plant {plant_name}")
            else:
                logger.warning(f"No valid temperature data for plant {plant_name}")
                
        except Exception as e:
            logger.error(f"Error collecting weather data for plant {plant_name}: {str(e)}")
    
    return weather_count

def main():
    """Main function to collect weather data"""
    args = parse_arguments()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate Growatt credentials
    if not Config.GROWATT_USERNAME or not Config.GROWATT_PASSWORD:
        logger.error("Growatt API credentials not configured")
        sys.exit(1)
    
    # Initialize Growatt API
    api = Growatt()
    
    # Try to authenticate
    try:
        login_success = api.login(Config.GROWATT_USERNAME, Config.GROWATT_PASSWORD)
        if not login_success:
            logger.error("Failed to authenticate with Growatt API")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        sys.exit(1)
    
    logger.info("Successfully authenticated with Growatt API")
    
    # Start time for performance tracking
    start_time = time.time()
    
    # Collect weather data
    weather_count = collect_weather_data(api, args.plant_id, args.debug)
    
    # Log results
    elapsed_time = time.time() - start_time
    logger.info(f"Weather data collection completed in {elapsed_time:.2f} seconds")
    logger.info(f"Weather data collected for {weather_count} plants")
    
    # Logout from API
    try:
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