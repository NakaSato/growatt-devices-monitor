import argparse
import datetime
import logging
import os
import json
from pathlib import Path

from app.config import Config
from app.data_collector import GrowattDataCollector
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_data_directories(base_dir):
    """Create organized directory structure for data storage"""
    directories = {
        'plants': Path(base_dir) / 'plants',
        'devices': Path(base_dir) / 'devices',
        'energy': Path(base_dir) / 'energy',
        'weather': Path(base_dir) / 'weather',
        'data_sync': Path(base_dir) / 'sync_results'
    }
    
    for dir_path in directories.values():
        dir_path.mkdir(exist_ok=True, parents=True)
    
    return directories

def save_json_output(data, filename, directory):
    """Save data as JSON to the specified directory"""
    if not data:
        logger.warning(f"No data to save for {filename}")
        return False
    
    output_path = Path(directory) / filename
    try:
        output_path.parent.mkdir(exist_ok=True, parents=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved JSON data to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON data to {output_path}: {e}")
        return False

def main():
    """Main function to run the data synchronization process"""
    parser = argparse.ArgumentParser(description='Sync data from Growatt API to local database')
    parser.add_argument('--init', action='store_true', help='Initialize the database before syncing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Add credential arguments to override config
    parser.add_argument('--username', type=str, help='Growatt API username')
    parser.add_argument('--password', type=str, help='Growatt API password')
    
    # Add specific data collection options
    data_group = parser.add_argument_group('Data Collection Options')
    data_group.add_argument('--plants', action='store_true', help='Fetch only plant data')
    data_group.add_argument('--devices', action='store_true', help='Fetch only device data')
    data_group.add_argument('--inverter-yield', action='store_true', help='Fetch inverter yield data')
    data_group.add_argument('--daily', action='store_true', help='Fetch daily energy statistics')
    data_group.add_argument('--monthly', action='store_true', help='Fetch monthly energy statistics')
    data_group.add_argument('--yearly', action='store_true', help='Fetch yearly energy statistics')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Override credentials with command line arguments if provided
    if args.username:
        Config.GROWATT_USERNAME = args.username
    if args.password:
        Config.GROWATT_PASSWORD = args.password
        
    # Validate credentials before proceeding
    if not Config.GROWATT_USERNAME or not Config.GROWATT_PASSWORD:
        logger.error("Growatt API credentials are missing. Please check your config or provide --username and --password arguments.")
        return
    
    # Use pathlib for better path handling
    base_dir = Path(__file__).parent
    data_dir = base_dir / 'data'
    
    # Create directories using pathlib
    data_dir.mkdir(exist_ok=True)
    logger.info(f"Data directory: {data_dir}")
    
    # Set up the organized directory structure
    dir_structure = setup_data_directories(data_dir)
    logger.info(f"Data will be stored in organized structure under: {data_dir}")
    
    # Also create a raw JSON output directory
    json_output_dir = data_dir / 'json_output'
    json_output_dir.mkdir(exist_ok=True)
    logger.info(f"Raw JSON data will be saved to: {json_output_dir}")
    
    start_time = datetime.datetime.now()
    logger.info(f"Starting data synchronization at {start_time}")
    
    # Initialize the database if requested
    if args.init:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized.")
    
    # Create and run the data collector
    collector = GrowattDataCollector(
        username=Config.GROWATT_USERNAME,
        password=Config.GROWATT_PASSWORD,
        save_to_file=True,
        data_dir=str(data_dir)  # Convert Path to string for compatibility
    )
    
    # Check if specific data types are requested
    specific_data_requested = any([
        args.plants, args.devices, args.inverter_yield,
        args.daily, args.monthly, args.yearly
    ])
    
    result = {}
    
    try:
        if specific_data_requested:
            # Collect only the requested data types
            logger.info("Collecting specific data types as requested")
            
            if args.plants:
                logger.info("Fetching plant data...")
                # Create a results dictionary to pass to _collect_plants_data
                plants_result = {'plants': 0, 'errors': []}
                result['plants'] = collector._collect_plants_data(plants_result)
                
            if args.devices:
                logger.info("Fetching device data...")
                result['devices'] = collector.get_devices()
                
            if args.inverter_yield:
                logger.info("Fetching inverter yield data...")
                result['inverter_yield'] = collector.get_inverter_yield()
                
            if args.daily:
                logger.info("Fetching daily energy statistics...")
                result['daily'] = collector.get_daily_energy()
                
            if args.monthly:
                logger.info("Fetching monthly energy statistics...")
                result['monthly'] = collector.get_monthly_energy()
                
            if args.yearly:
                logger.info("Fetching yearly energy statistics...")
                result['yearly'] = collector.get_yearly_energy()
            
            # Prepare a summary result
            summary = {
                'success': True,
                'message': 'Specific data collection completed',
                'data': result,
                'results': {
                    k: len(v) if isinstance(v, list) else 1 if v else 0 
                    for k, v in result.items() if v
                }
            }
            result = summary
        else:
            # Run normal full data collection
            logger.info("Performing full data collection...")
            result = collector.collect_and_store_all_data()
        
        # Save the complete result as JSON for reference
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Save the complete result to the data directory
        save_json_output(result, f"sync_result_{timestamp}.json", dir_structure['data_sync'])
        
        # Additionally, save each component data if available in the result
        if result.get('success') and 'data' in result:
            data = result.get('data', {})
            for data_type, data_content in data.items():
                if data_content:
                    # Save to appropriate directory based on data type
                    target_dir = dir_structure.get(data_type, data_dir)
                    save_json_output(
                        data_content, 
                        f"{data_type}_{timestamp}.json", 
                        target_dir
                    )
        
        if result.get('success'):
            stats = result.get('results', {})
            logger.info(f"Data sync complete. Stats: Plants: {stats.get('plants', 0)}, "
                       f"Devices: {stats.get('devices', 0)}, Energy records: {stats.get('energy_stats', 0)}, "
                       f"Weather records: {stats.get('weather', 0)}")
            
            if stats.get('errors'):
                logger.warning(f"There were {len(stats.get('errors', []))} errors during sync")
                for error in stats.get('errors', []):
                    logger.warning(f"Error: {error}")
        else:
            logger.error(f"Data sync failed: {result.get('message')}")
    
    except Exception as e:
        logger.exception(f"Unexpected error during data synchronization: {e}")
        result = {'success': False, 'message': f"Sync failed with exception: {str(e)}"}
        
    finally:
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info(f"Data synchronization completed in {duration.total_seconds():.2f} seconds")
        return 0 if result.get('success', False) else 1

if __name__ == "__main__":
    exit(main())
