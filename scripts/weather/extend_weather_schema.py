#!/usr/bin/env python3
"""
Extend Weather Data Schema

This script extends the weather_data table in the database to store all the weather data fields
returned by the Growatt API. It also creates a new function in the DatabaseConnector class
to save the complete weather data.

Usage:
    python extend_weather_schema.py
"""

import os
import sys
import logging
import argparse
import psycopg2
from psycopg2.extras import Json

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app modules
from app.config import Config
from app.database import get_db_connection, DatabaseConnector

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
    parser = argparse.ArgumentParser(description='Extend the weather data schema')
    parser.add_argument('--dry-run', action='store_true', help='Print SQL statements without executing them')
    return parser.parse_args()

def extend_weather_schema(dry_run=False):
    """
    Extends the weather_data table to include additional columns for all weather data fields.
    
    Args:
        dry_run (bool): If True, only print the SQL statements without executing them
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        new_columns = [
            ("env_humidity", "REAL", "Relative humidity percentage"),
            ("panel_temp", "REAL", "Solar panel temperature in degrees Celsius"),
            ("wind_speed", "REAL", "Wind speed in m/s"),
            ("wind_angle", "INTEGER", "Wind direction in degrees"),
            ("datalog_sn", "TEXT", "Serial number of the data logger"),
            ("device_status", "TEXT", "Status of the weather monitoring device"),
            ("lost", "BOOLEAN", "Whether the device is offline"),
            ("irradiation", "REAL", "Solar irradiation value"),
            ("air_pressure", "REAL", "Atmospheric pressure"),
            ("rainfall_intensity", "REAL", "Rainfall intensity"),
            ("raw_data", "JSONB", "Complete raw data from the API")
        ]
        
        # SQL to check if a column exists
        check_column_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'weather_data' AND column_name = %s
        """
        
        # SQL to add a new column
        add_column_sql = """
            ALTER TABLE weather_data 
            ADD COLUMN IF NOT EXISTS {} {} 
            -- {}
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for column_name, column_type, comment in new_columns:
                # Check if column already exists
                cursor.execute(check_column_sql, (column_name,))
                exists = cursor.fetchone() is not None
                
                if not exists:
                    sql = add_column_sql.format(column_name, column_type, comment)
                    if dry_run:
                        logger.info(f"Would execute: {sql}")
                    else:
                        logger.info(f"Adding column: {column_name} ({column_type})")
                        cursor.execute(sql)
                else:
                    logger.info(f"Column already exists: {column_name}")
            
            if not dry_run:
                conn.commit()
                logger.info("Weather data schema extended successfully")
            else:
                logger.info("Dry run completed - no changes made")
                
        return True
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error extending weather schema: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error extending weather schema: {e}")
        return False

def add_save_complete_weather_data():
    """
    Adds the save_complete_weather_data method to the DatabaseConnector class.
    This doesn't actually add the method to the class in memory, but shows the code to add to the file.
    """
    method_code = """
    def save_complete_weather_data(self, plant_id: str, weather_data: Dict[str, Any]) -> bool:
        \"\"\"
        Save complete weather data to the database.
        
        Args:
            plant_id: Plant ID
            weather_data: Complete weather data dictionary from the API
            
        Returns:
            bool: True if successful, False otherwise
        \"\"\"
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
                
                cursor.execute(
                    \"\"\"
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
                    \"\"\",
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
                conn.commit()
                
                logger.info(f"Saved complete weather data for plant {plant_id}")
                return True
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error saving complete weather data: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving complete weather data: {e}")
            return False
    """
    
    # Print the code to add to the DatabaseConnector class
    logger.info("Add the following method to the DatabaseConnector class in app/database.py:")
    print("\n" + method_code)

def main():
    """Main function"""
    args = parse_arguments()
    
    # Extend the weather schema
    if extend_weather_schema(args.dry_run):
        logger.info("Weather schema extension completed successfully")
    else:
        logger.error("Failed to extend weather schema")
        sys.exit(1)
    
    # Print the method to add to the DatabaseConnector class
    add_save_complete_weather_data()
    
    # Provide instructions for updating the weather collector script
    logger.info("\nNext steps:")
    logger.info("1. Add the save_complete_weather_data method to the DatabaseConnector class in app/database.py")
    logger.info("2. Update the weather collector script to use the new method")
    logger.info("3. Run the updated weather collector to collect comprehensive weather data")

if __name__ == "__main__":
    main() 