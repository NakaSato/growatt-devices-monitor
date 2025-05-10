#!/usr/bin/env python3
"""
Script to manually collect all Growatt data and save to the Postgres database

This script uses the data collection endpoint to collect all available data
from the Growatt API and save it to the PostgreSQL database.
"""

import os
import sys
import json
import logging
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Import from the app for direct access
from app.config import Config
from app.database import DatabaseConnector, get_db_connection
from app.core.growatt import Growatt

# Import our new weather data collector
from script.collect_weather_data import WeatherDataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'collect_all_data.log'))
    ]
)
logger = logging.getLogger("collect_all_data")

def ensure_logs_dir():
    """Ensure logs directory exists"""
    logs_dir = os.path.join(parent_dir, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        logger.info(f"Created logs directory at {logs_dir}")

def collect_all_data(server_url, days_back=7, include_weather=True, save_to_file=False):
    """
    Trigger data collection via API endpoint

    Args:
        server_url: URL of the server running the Growatt monitor
        days_back: Number of days of historical data to collect
        include_weather: Whether to collect weather data
        save_to_file: Whether to save raw data to JSON files

    Returns:
        dict: Collection results
    """
    url = f"{server_url}/api/data/collect"

    data = {
        "days_back": days_back,
        "include_weather": include_weather,
        "collect_all": True,
        "save_to_file": save_to_file
    }

    logger.info(f"Sending request to {url} with parameters: {data}")

    try:
        response = requests.post(url, json=data, timeout=300)  # 5-minute timeout

        if response.status_code == 200:
            result = response.json()
            stats = result.get('stats', {})
            logger.info(f"Collection successful: {stats.get('plants', 0)} plants, "
                        f"{stats.get('devices', 0)} devices, "
                        f"{stats.get('energy_stats', 0)} energy records, "
                        f"{stats.get('weather', 0)} weather records, "
                        f"{result.get('json_data_count', 0)} JSON data items")
            # Ensure 'success' field is set to True on successful responses
            result['success'] = True
            return result
        else:
            logger.error(f"Collection failed with status code {response.status_code}: {response.text}")
            return {"success": False, "message": f"HTTP error: {response.status_code}"}

    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return {"success": False, "message": str(e)}

def save_to_postgres(data, days_back=7, include_weather=True):
    """
    Save collected data directly to the PostgreSQL database

    Args:
        data: Dict containing JSON data from Growatt API
        days_back: Number of days of historical data to collect
        include_weather: Whether to collect weather data

    Returns:
        dict: Collection statistics
    """
    logger.info("Saving data directly to PostgreSQL database")

    try:
        # Initialize database connector
        db_connector = DatabaseConnector()

        # Extract data from the JSON
        plants = data.get('plants', [])
        devices = data.get('devices', [])
        energy_stats = data.get('energy_stats', [])
        weather_data = data.get('weather', [])

        # Save plants data
        logger.info(f"Saving {len(plants)} plants to database")
        db_connector.save_plant_data(plants)

        # Save devices data
        logger.info(f"Saving {len(devices)} devices to database")
        db_connector.save_device_data(devices)

        # Save energy stats data
        logger.info(f"Saving {len(energy_stats)} energy records to database")
        saved_energy = db_connector.save_energy_data_batch(energy_stats)

        # Save weather data if requested
        weather_count = 0
        if include_weather and weather_data:
            logger.info(f"Saving {len(weather_data)} weather records to database")
            for weather in weather_data:
                if db_connector.save_weather_data(
                    plant_id=weather.get('plant_id'),
                    date=weather.get('date'),
                    temperature=weather.get('temperature'),
                    condition=weather.get('condition')
                ):
                    weather_count += 1

        # Prepare statistics
        stats = {
            'plants': len(plants),
            'devices': len(devices),
            'energy_stats': saved_energy,
            'weather': weather_count
        }

        logger.info(f"Database save completed: {stats['plants']} plants, "
                    f"{stats['devices']} devices, "
                    f"{stats['energy_stats']} energy records, "
                    f"{stats['weather']} weather records")

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.error(f"Error saving to PostgreSQL database: {str(e)}")
        return {
            'success': False,
            'message': f"Database error: {str(e)}"
        }

def save_files_to_db(dir_path, plant_id=None, device_id=None, recursive=False):
    """
    Save all files from a directory to the PostgreSQL database

    Args:
        dir_path: Directory path containing files to save
        plant_id: Optional plant ID to associate with the files
        device_id: Optional device ID to associate with the files
        recursive: Whether to recursively search subdirectories

    Returns:
        dict: Results of the operation
    """
    import os
    import mimetypes
    import json
    from datetime import datetime

    # Initialize database connector
    db_connector = DatabaseConnector()

    # Initialize statistics
    stats = {
        'total_files': 0,
        'saved_files': 0,
        'failed_files': 0,
        'skipped_files': 0,
        'total_size_bytes': 0
    }

    # List of saved, failed, and skipped files
    saved_files = []
    failed_files = []
    skipped_files = []

    # Ensure directory exists
    if not os.path.exists(dir_path):
        logger.error(f"Directory not found: {dir_path}")
        return {
            'success': False,
            'message': f"Directory not found: {dir_path}",
            'stats': stats
        }

    # Get list of files
    all_files = []
    if recursive:
        for root, _, files in os.walk(dir_path):
            for filename in files:
                all_files.append(os.path.join(root, filename))
    else:
        all_files = [os.path.join(dir_path, f) for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))]

    logger.info(f"Found {len(all_files)} files in {dir_path}")
    stats['total_files'] = len(all_files)

    # Process each file
    for file_path in all_files:
        # Get file information
        filename = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, os.path.dirname(dir_path))

        # Skip files that already exist in the database
        if db_connector.file_exists_in_db(rel_path):
            logger.info(f"Skipping existing file: {rel_path}")
            stats['skipped_files'] += 1
            skipped_files.append(rel_path)
            continue

        try:
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()

            # Get file size
            size_bytes = len(content)
            stats['total_size_bytes'] += size_bytes

            # Get file type
            file_type = mimetypes.guess_type(file_path)[0]
            if not file_type:
                # Try to determine type from extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.json']:
                    file_type = 'application/json'
                elif ext in ['.csv']:
                    file_type = 'text/csv'
                elif ext in ['.txt']:
                    file_type = 'text/plain'
                else:
                    file_type = 'application/octet-stream'

            # Extract metadata from JSON files
            metadata = None
            if file_type == 'application/json':
                try:
                    # Try to parse as JSON to extract metadata
                    json_data = json.loads(content.decode('utf-8'))
                    # Extract basic metadata
                    metadata = {
                        'record_count': len(json_data) if isinstance(json_data, list) else 1,
                        'data_type': 'array' if isinstance(json_data, list) else 'object',
                        'keys': list(json_data.keys()) if isinstance(json_data, dict) else None
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON file: {rel_path}")

            # Save file to database
            success = db_connector.save_file_to_db(
                filename=filename,
                file_path=rel_path,
                content=content,
                file_type=file_type,
                plant_id=plant_id,
                device_id=device_id,
                metadata=metadata
            )

            if success:
                logger.info(f"Saved file to database: {rel_path} ({size_bytes} bytes)")
                stats['saved_files'] += 1
                saved_files.append(rel_path)
            else:
                logger.error(f"Failed to save file: {rel_path}")
                stats['failed_files'] += 1
                failed_files.append(rel_path)

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            stats['failed_files'] += 1
            failed_files.append(rel_path)

    # Calculate success percentage
    if stats['total_files'] > 0:
        success_percentage = (stats['saved_files'] / stats['total_files']) * 100
    else:
        success_percentage = 0

    # Format size in human-readable format
    human_readable_size = format_file_size(stats['total_size_bytes'])

    # Prepare result
    result = {
        'success': stats['failed_files'] == 0,
        'stats': stats,
        'saved_files': saved_files,
        'failed_files': failed_files,
        'skipped_files': skipped_files,
        'human_readable_size': human_readable_size,
        'success_percentage': success_percentage
    }

    logger.info(f"File save operation completed: {stats['saved_files']} saved, "
                f"{stats['failed_files']} failed, {stats['skipped_files']} skipped, "
                f"total size: {human_readable_size}")

    return result

def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024 or unit == 'TB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def collect_direct_from_api(username, password, days_back=7, include_weather=True):
    """
    Collect data directly from Growatt API without using the web app

    Args:
        username: Growatt account username
        password: Growatt account password
        days_back: Number of days of historical data to collect
        include_weather: Whether to collect weather data

    Returns:
        dict: Collected data and statistics
    """
    logger.info(f"Collecting data directly from Growatt API (days_back={days_back})")

    try:
        # Initialize Growatt API client
        api = Growatt()

        # Login to Growatt API
        login_result = api.login(username, password)
        if not login_result.get('success', False):
            return {
                'success': False,
                'message': f"Growatt login failed: {login_result.get('msg', 'Unknown error')}"
            }

        logger.info("Successfully logged in to Growatt API")

        # Get plant list
        plants_result = api.get_plant_list()
        if not plants_result.get('success', False):
            return {
                'success': False,
                'message': f"Failed to get plant list: {plants_result.get('msg', 'Unknown error')}"
            }

        plants = plants_result.get('data', [])
        logger.info(f"Found {len(plants)} plants")

        # Collect devices for each plant
        all_devices = []
        for plant in plants:
            plant_id = plant.get('id')
            devices_result = api.get_plant_devices(plant_id)
            if devices_result.get('success', False):
                plant_devices = devices_result.get('data', [])
                for device in plant_devices:
                    device['plant_id'] = plant_id
                all_devices.extend(plant_devices)
            else:
                logger.warning(f"Failed to get devices for plant {plant_id}")

        logger.info(f"Found {len(all_devices)} devices")

        # Collect energy stats for each device
        all_energy_stats = []
        for device in all_devices:
            sn = device.get('sn') or device.get('serialNumber')
            if not sn:
                continue

            energy_result = api.get_energy_data(sn, days_back=days_back)
            if energy_result.get('success', False):
                energy_data = energy_result.get('data', [])
                for data in energy_data:
                    data['mix_sn'] = sn
                    data['plant_id'] = device.get('plant_id')
                all_energy_stats.extend(energy_data)
            else:
                logger.warning(f"Failed to get energy stats for device {sn}")

        logger.info(f"Collected {len(all_energy_stats)} energy records")

        # Collect weather data if requested
        all_weather = []
        if include_weather:
            for plant in plants:
                plant_id = plant.get('id')
                weather_result = api.get_weather_data(plant_id, days_back=days_back)
                if weather_result.get('success', False):
                    weather_data = weather_result.get('data', [])
                    for data in weather_data:
                        data['plant_id'] = plant_id
                    all_weather.extend(weather_data)
                else:
                    logger.warning(f"Failed to get weather data for plant {plant_id}")

            logger.info(f"Collected {len(all_weather)} weather records")

        # Prepare collected data
        collected_data = {
            'plants': plants,
            'devices': all_devices,
            'energy_stats': all_energy_stats,
            'weather': all_weather
        }

        return {
            'success': True,
            'data': collected_data,
            'stats': {
                'plants': len(plants),
                'devices': len(all_devices),
                'energy_stats': len(all_energy_stats),
                'weather': len(all_weather)
            }
        }

    except Exception as e:
        logger.error(f"Error collecting data from Growatt API: {str(e)}")
        return {
            'success': False,
            'message': f"API error: {str(e)}"
        }

def collect_weather_data(days=7):
    """
    Collect weather data for all plants
    
    Args:
        days: Number of days of data to collect
        
    Returns:
        dict: Weather collection statistics
    """
    logger.info(f"Collecting weather data for {days} days")
    
    try:
        # Initialize the weather data collector
        collector = WeatherDataCollector(days=days)
        
        # Run the collector
        result = collector.run()
        
        if result == 0:
            logger.info("Weather data collection completed successfully")
            return {"success": True}
        else:
            logger.error(f"Weather data collection failed with exit code {result}")
            return {"success": False, "message": f"Exit code: {result}"}
            
    except Exception as e:
        logger.error(f"Error collecting weather data: {str(e)}")
        return {"success": False, "message": str(e)}

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Collect all Growatt data and save to database')
    parser.add_argument('--server', type=str, help='Server URL where the Growatt Monitor is running')
    parser.add_argument('--days', type=int, default=7, help='Number of days of historical data to collect')
    parser.add_argument('--save-files', action='store_true', help='Save raw data to JSON files')
    parser.add_argument('--no-weather', action='store_true', help='Skip weather data collection')
    parser.add_argument('--weather-only', action='store_true', help='Only collect weather data')
    parser.add_argument('--direct', action='store_true', help='Collect directly from Growatt API')
    parser.add_argument('--import-dir', type=str, help='Import JSON files from directory')
    parser.add_argument('--recursive', action='store_true', help='Recursively search import directory')
    parser.add_argument('--plant-id', type=str, help='Plant ID for file imports')
    parser.add_argument('--device-id', type=str, help='Device ID for file imports')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('app').setLevel(logging.DEBUG)
    
    # Ensure logs directory exists
    ensure_logs_dir()
    
    # Track stats for summary
    all_stats = {}
    success = True
    
    # Handle weather-only mode
    if args.weather_only:
        weather_result = collect_weather_data(days=args.days)
        return 0 if weather_result['success'] else 1
    
    # Handle direct API collection
    if args.direct:
        # Get Growatt credentials from environment or config
        username = os.environ.get('GROWATT_USERNAME', Config.GROWATT_USERNAME)
        password = os.environ.get('GROWATT_PASSWORD', Config.GROWATT_PASSWORD)
        
        if not username or not password:
            logger.error("Growatt username and password must be provided for direct API collection")
            return 1
            
        logger.info(f"Collecting data directly from Growatt API for the past {args.days} days")
        
        # Collect data from Growatt API
        result = collect_direct_from_api(
            username=username,
            password=password,
            days_back=args.days,
            include_weather=not args.no_weather
        )
        
        all_stats['direct_api'] = result.get('stats', {})
        success = result.get('success', False)
        
        # Collect weather data separately if needed
        if not args.no_weather:
            weather_result = collect_weather_data(days=args.days)
            all_stats['weather'] = weather_result
            success = success and weather_result.get('success', False)
            
    # Handle API endpoint collection
    elif args.server:
        logger.info(f"Collecting data from API endpoint at {args.server}")
        
        # Call API endpoint to collect data
        result = collect_all_data(
            server_url=args.server,
            days_back=args.days,
            include_weather=not args.no_weather,
            save_to_file=args.save_files
        )
        
        all_stats['api'] = result.get('stats', {})
        success = result.get('success', False)
        
        # Collect weather data separately if needed
        if not args.no_weather:
            weather_result = collect_weather_data(days=args.days)
            all_stats['weather'] = weather_result
            success = success and weather_result.get('success', False)
            
    # Handle file import
    elif args.import_dir:
        logger.info(f"Importing files from {args.import_dir}")
        
        # Save files to database
        result = save_files_to_db(
            dir_path=args.import_dir,
            plant_id=args.plant_id,
            device_id=args.device_id,
            recursive=args.recursive
        )
        
        all_stats['import'] = result.get('stats', {})
        success = result.get('success', False)
    
    else:
        logger.error("No action specified. Use --server, --direct, or --import-dir")
        parser.print_help()
        return 1
    
    # Print summary
    logger.info("Collection summary:")
    for key, stats in all_stats.items():
        if isinstance(stats, dict) and 'stats' in stats:
            stats = stats['stats']
        logger.info(f"- {key}: {stats}")
    
    return 0 if success else 1
    
if __name__ == "__main__":
    sys.exit(main())
