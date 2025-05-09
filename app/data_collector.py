import logging
import os
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta, date
import time
import pytz

# Fix the imports from app.core.growatt - use Growatt class instead of GrowattAPI
from app.core.growatt import Growatt
from app.config import Config  # Import the Config class
from app.database import DatabaseConnector

# Get application timezone
def get_timezone():
    """Get the application timezone from environment or default to Asia/Bangkok"""
    tz_name = os.environ.get('TIMEZONE', 'Asia/Bangkok')
    try:
        return pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        logging.warning(f"Unknown timezone: {tz_name}, falling back to UTC")
        return pytz.UTC
from app.services.device_status_tracker import DeviceStatusTracker

# Configure logging
logger = logging.getLogger(__name__)

class GrowattDataCollector:
    """Collects data from Growatt API and stores it in the database"""
    
    def __init__(self, username=None, password=None, data_dir=None, save_to_file=False):
        """
        Initialize the data collector with database connector
        
        Args:
            username: Optional username to override Config
            password: Optional password to override Config
            data_dir: Optional directory to save data files
            save_to_file: Whether to save data to files
        """
        self.db = DatabaseConnector()
        self.authenticated = False
        self.retry_count = 3
        self.retry_delay = 2  # seconds
        # Initialize the API client
        self.api = Growatt()
        
        # Initialize the device status tracker for notifications
        self.device_tracker = DeviceStatusTracker()
        
        # Store credentials
        self.username = username or Config.GROWATT_USERNAME
        self.password = password or Config.GROWATT_PASSWORD
        
        # JSON data collection
        self.collect_json = False
        self.json_data = []
        
        # File saving options
        self.data_dir = data_dir or 'data'
        self.save_to_file = save_to_file
        
        # Create data directory if it doesn't exist
        if self.save_to_file and not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def enable_json_collection(self):
        """Enable collection of raw JSON data"""
        self.collect_json = True
        self.json_data = []
    
    def _add_json_data(self, data_type: str, data: Any, plant_id: str = None, 
                       device_sn: str = None, source: str = None):
        """
        Add JSON data to the collection if enabled
        
        Args:
            data_type: Type of data (plants, devices, energy, weather)
            data: Data to store (will be converted to JSON)
            plant_id: Optional plant ID
            device_sn: Optional device serial number
            source: Optional source identifier
        """
        if not self.collect_json:
            return
            
        try:
            # Handle data serialization with unicode characters
            content = json.dumps(data, ensure_ascii=False)
            self.json_data.append({
                'type': data_type,
                'content': content,
                'plant_id': plant_id,
                'device_sn': device_sn,
                'source': source,
                'timestamp': datetime.now(get_timezone()).isoformat()
            })
        except Exception as e:
            logger.error(f"Error adding JSON data: {str(e)}")
    
    def authenticate(self):
        """
        Authenticate with the Growatt API
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        # Validate credentials before attempting authentication
        if not self.username:
            logger.error("Missing API credentials: Username not configured. Please check your environment variables or .env file.")
            return False
            
        if not self.password:
            logger.error("Missing API credentials: Password not configured. Please check your environment variables or .env file.")
            return False
            
        logger.debug(f"Attempting authentication with username: {self.username}")
        
        for attempt in range(self.retry_count):
            try:
                # Use the API instance with explicitly checked credentials
                login_result = self.api.login(username=self.username, 
                                              password=self.password)
                
                if not login_result:
                    logger.error("Authentication failed: Invalid credentials or API error")
                    if attempt < self.retry_count - 1:
                        logger.info(f"Retrying authentication (attempt {attempt + 2}/{self.retry_count})")
                        time.sleep(self.retry_delay)
                    continue
                    
                self.authenticated = True
                logger.info("Successfully authenticated with Growatt API")
                return True
            except Exception as e:
                logger.error(f"Authentication error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                logger.debug(f"Authentication error details: ", exc_info=True)
                if attempt < self.retry_count - 1:
                    logger.info(f"Retrying authentication in {self.retry_delay} seconds")
                    time.sleep(self.retry_delay)
        
        logger.error(f"Authentication failed after {self.retry_count} attempts")
        return False
    
    def _safe_api_call(self, func, *args, **kwargs) -> Any:
        """
        Safely call API functions with retry logic
        
        Args:
            func: Function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call or None if all retry attempts fail
        """
        func_name = getattr(func, '__name__', str(func))
        logger.debug(f"Calling API function: {func_name} with args: {args} and kwargs: {kwargs}")
        
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.retry_count} for {func_name}")
                result = func(*args, **kwargs)
                
                # Debug log the response (truncated if too large)
                result_str = str(result)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "... [truncated]"
                logger.debug(f"API response for {func_name}: {result_str}")
                
                # Log type and structure of the response
                if result is not None:
                    logger.debug(f"Response type: {type(result)}")
                    if hasattr(result, 'keys') and callable(result.keys):
                        logger.debug(f"Response keys: {list(result.keys())}")
                    elif isinstance(result, (list, tuple)):
                        logger.debug(f"Response length: {len(result)}")
                        if result and hasattr(result[0], 'keys') and callable(result[0].keys):
                            logger.debug(f"First item keys: {list(result[0].keys())}")
                
                # Store JSON data if collection is enabled
                if self.collect_json:
                    # Extract metadata from function and args to determine data type
                    data_type = 'unknown'
                    plant_id = None
                    device_sn = None
                    
                    if 'plant' in func_name.lower():
                        data_type = 'plants'
                    elif 'device' in func_name.lower():
                        data_type = 'devices'
                        if len(args) > 0:
                            plant_id = args[0]
                    elif 'energy' in func_name.lower():
                        data_type = 'energy'
                        if kwargs.get('plant_id'):
                            plant_id = kwargs.get('plant_id')
                        if kwargs.get('device_sn'):
                            device_sn = kwargs.get('device_sn')
                    elif 'weather' in func_name.lower():
                        data_type = 'weather'
                        if len(args) > 0:
                            plant_id = args[0]
                    
                    self._add_json_data(
                        data_type=data_type,
                        data=result,
                        plant_id=plant_id,
                        device_sn=device_sn,
                        source=func_name
                    )
                
                # Check for common API error patterns
                if isinstance(result, dict):
                    if result.get('error') or result.get('result') == False or result.get('success') == False:
                        error_msg = result.get('msg', 'Unknown API error')
                        logger.error(f"API error in response: {error_msg}")
                        
                        # Check if session expired
                        if 'session' in error_msg.lower() or 'login' in error_msg.lower() or 'auth' in error_msg.lower():
                            logger.info("Session may have expired, attempting to re-authenticate")
                            if self.authenticate():
                                logger.info("Re-authentication successful, retrying API call")
                                continue
                
                return result
            except Exception as e:
                logger.error(f"API call error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                logger.debug("Exception details:", exc_info=True)
                
                if attempt < self.retry_count - 1:
                    logger.info(f"Retrying API call in {self.retry_delay} seconds")
                    time.sleep(self.retry_delay)
                    
                    # If this is the second attempt, try re-authenticating
                    if attempt == 1:
                        logger.info("Attempting to re-authenticate before retry")
                        if self.authenticate():
                            logger.info("Re-authentication successful")
        
        logger.critical(f"Failed to call {func_name} after {self.retry_count} attempts")
        return None  # Return None instead of raising to allow partial data collection
    
    def collect_and_store_all_data(self, days_back: int = 7, include_weather: bool = True) -> Dict[str, Any]:
        """
        Collect and store all data from Growatt API
        
        Args:
            days_back: Number of days of historical data to collect
            include_weather: Whether to collect weather data
            
        Returns:
            dict: Collection results with success status and statistics
        """
        # Check if credentials exist before attempting authentication
        if not self.username or not self.password:
            logger.error("Authentication failed: Missing credentials")
            return {"success": False, "message": "Authentication failed: Missing credentials"}
            
        if not self.authenticated and not self.authenticate():
            logger.error("Authentication failed: Invalid credentials or API error")
            return {"success": False, "message": "Authentication failed: Invalid credentials or API error"}
            
        results = {
            "plants": 0,
            "devices": 0,
            "energy_stats": 0,
            "weather": 0,
            "errors": [],
            "skipped_plants": [],
            "skipped_devices": []
        }
        
        # Reset JSON data collection
        if self.collect_json:
            self.json_data = []
        
        try:
            # Use the api instance to get plants
            logger.info("Fetching plant list from API")
            plants = self._safe_api_call(self.api.get_plants)
            
            if not plants:
                logger.error("No plants data returned from API")
                return {"success": False, "message": "No plants data returned from API"}
                
            if not isinstance(plants, list):
                logger.error(f"Unexpected plants data format: {type(plants)}")
                return {"success": False, "message": f"Unexpected plants data format: {type(plants)}"}
            
            if len(plants) == 0:
                logger.warning("Plants list is empty")
            
            logger.info(f"Successfully retrieved {len(plants)} plants")
            
            plant_store_result = self.db.save_plant_data(plants)
            if plant_store_result:
                results["plants"] = len(plants)
            
            # For each plant, collect and store devices, energy data, and weather
            all_devices = []  # Store all device data for status tracking
            for plant_index, plant in enumerate(plants):
                plant_id = plant.get('id')
                plant_name = plant.get('name', 'Unknown')
                if not plant_id:
                    logger.warning(f"Skipping plant with no ID: {plant}")
                    results["skipped_plants"].append(f"Missing ID: {plant_name}")
                    continue
                
                logger.info(f"Processing plant {plant_index+1}/{len(plants)}: {plant_name} (ID: {plant_id})")
                
                try:
                    # Use the api instance to get devices
                    logger.info(f"Fetching devices for plant {plant_id}")
                    devices = self._safe_api_call(self.api.get_device_list, plant_id)
                    
                    if isinstance(devices, list):
                        device_data = devices
                    elif isinstance(devices, dict) and 'datas' in devices:
                        device_data = devices.get('datas', [])
                    else:
                        device_data = []
                    
                    # Transform device data to match database schema
                    transformed_devices = []
                    for device in device_data:
                        sn = device.get('sn')
                        if not sn:
                            logger.warning(f"Skipping device with no serial number: {device}")
                            results["skipped_devices"].append(f"Missing SN: {device.get('alias', 'Unknown')} in plant {plant_name}")
                            continue
                        
                        device_type = device.get('deviceType')
                        device_status = device.get('status', 'unknown')
                        last_update = device.get('lastUpdateTime') or datetime.now(get_timezone()).isoformat()
                        
                        # Handle offline status
                        is_offline = device.get('lost') == 'true' or device_status == '0'
                        if is_offline:
                            device_status = 'offline'
                        elif device_status == '1':
                            device_status = 'online'
                        else:
                            device_status = 'unknown'
                        
                        # Log device information for debugging
                        logger.debug(f"Processing device: SN={sn}, Type={device_type}, Status={device_status}, Offline={is_offline}")
                        
                        # Convert datetime objects to strings in raw_data for proper JSON serialization for PostgreSQL
                        raw_data = {}
                        for key, value in device.items():
                            # Handle datetime objects by converting to ISO format strings
                            if isinstance(value, datetime):
                                raw_data[key] = value.isoformat()
                            else:
                                raw_data[key] = value
                        
                        # Store current time as ISO format string
                        current_time = datetime.now(get_timezone()).isoformat()
                        
                        # Create the device entry with standardized field names
                        device_entry = {
                            "serial_number": sn,
                            "plant_id": plant_id,
                            "plant_name": plant_name,
                            "alias": device.get('alias', ''),
                            "type": device_type,
                            "status": device_status,
                            "last_update_time": last_update,  # Add this field that's expected by the front end
                            "last_updated": current_time,  # Add this field that's expected by database
                            "raw_data": raw_data  # Store the preprocessed raw device data
                        }
                        
                        # Convert string last_update_time to datetime if it's a string
                        if isinstance(device_entry["last_update_time"], str):
                            try:
                                # Try to parse the datetime string to ensure it's valid
                                datetime.strptime(device_entry["last_update_time"], "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                # If parsing fails, use current time
                                device_entry["last_update_time"] = current_time
                        
                        transformed_devices.append(device_entry)
                        all_devices.append(device_entry)
                    
                    if transformed_devices:
                        device_store_result = self.db.save_device_data(transformed_devices)
                        if device_store_result:
                            results["devices"] += len(transformed_devices)
                    
                    # Collect energy data for each device - continue even if some devices fail
                    for device_index, device in enumerate(device_data):
                        sn = device.get('sn')
                        device_alias = device.get('alias', 'Unknown')
                        if not sn:
                            logger.warning(f"Skipping device with no serial number: {device}")
                            results["skipped_devices"].append(f"Missing SN: {device_alias} in plant {plant_name}")
                            continue
                        
                        try:
                            logger.info(f"Collecting energy data for device {device_index+1}/{len(device_data)}: {device_alias} (SN: {sn})")
                            # Get energy data for the specified number of days
                            self._collect_device_energy_data(plant_id, sn, results, days_back)
                        except Exception as device_err:
                            error_msg = f"Error processing device {sn} ({device_alias}): {str(device_err)}"
                            logger.error(error_msg)
                            results["errors"].append(error_msg)
                            # Continue with next device
                    
                    # Collect and store weather data if requested - don't let failure stop the process
                    if include_weather:
                        try:
                            logger.info(f"Collecting weather data for plant {plant_id}")
                            self._collect_weather_data(plant_id, results)
                        except Exception as weather_err:
                            error_msg = f"Weather data error for plant {plant_id} ({plant_name}): {str(weather_err)}"
                            logger.error(error_msg)
                            results["errors"].append(weather_err)
                    
                except Exception as plant_err:
                    error_msg = f"Error processing plant {plant_id} ({plant_name}): {str(plant_err)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    # Continue with next plant
            
            # Add JSON data to results if collection is enabled
            if self.collect_json:
                results["json_data"] = self.json_data
                logger.info(f"Collected {len(self.json_data)} JSON data items")
            
            # Check device status and send notifications if needed
            if all_devices:
                logger.info(f"Checking status of {len(all_devices)} devices for notifications")
                notification_results = self.device_tracker.check_and_notify_status_changes(all_devices)
                
                # Add notification results to the overall results
                results["notifications"] = {
                    "offline_notifications": notification_results.get('offline', 0),
                    "online_notifications": notification_results.get('online', 0)
                }
                
                logger.info(f"Notification check completed: {notification_results.get('offline', 0)} offline notifications, "
                           f"{notification_results.get('online', 0)} online notifications sent")
            
            # Data collection is a success if we got any data, even with some errors
            success = results["plants"] > 0 or results["devices"] > 0 or results["energy_stats"] > 0
            message = "Data collection completed successfully"
            if results["errors"]:
                message = "Data collection completed with some errors"
                
            return {
                "success": success, 
                "results": results,
                "message": message,
                "json_data": self.json_data if self.collect_json else None
            }
        except Exception as e:
            logger.error(f"Error collecting data: {str(e)}", exc_info=True)
            results["errors"].append(str(e))
            
            # Add JSON data to results even on failure if collection is enabled
            if self.collect_json:
                results["json_data"] = self.json_data
            
            # Return partial results even on failure
            return {
                "success": False, 
                "message": str(e), 
                "results": results,
                "has_partial_data": results["plants"] > 0 or results["devices"] > 0 or results["energy_stats"] > 0,
                "json_data": self.json_data if self.collect_json else None
            }
    
    def _collect_device_energy_data(self, plant_id: str, device_sn: str, 
                                    results: Dict[str, Any], days_back: int = 7) -> None:
        """
        Collect energy data for a specific device
        
        Args:
            plant_id: Plant ID
            device_sn: Device serial number
            results: Results dictionary to update
            days_back: Number of days of historical data to collect
        """
        try:
            # Get data for the specified number of days
            end_date = datetime.now(get_timezone())
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            logger.debug(f"Fetching energy data for device {device_sn} from {start_date_str} to {end_date_str}")
            
            # Call Growatt API to get energy data - use self.api instance
            energy_data = self._safe_api_call(self.api.get_energy_stats,
                                              plant_id=plant_id,
                                              device_sn=device_sn,
                                              start_date=start_date_str,
                                              end_date=end_date_str)
            
            if not energy_data:
                logger.warning(f"No energy data returned for device {device_sn}")
                return
                
            # Process energy data
            batch_data = []
            if isinstance(energy_data, dict) and 'data' in energy_data:
                data_points = energy_data.get('data', [])
                
                for data_point in data_points:
                    date = data_point.get('date')
                    energy = data_point.get('energy', 0.0)
                    peak_power = data_point.get('peak_power')
                    
                    if date and energy is not None:
                        batch_data.append({
                            'plant_id': plant_id,
                            'mix_sn': device_sn,
                            'date': date,
                            'daily_energy': float(energy),
                            'peak_power': peak_power
                        })
            
            # Save batch data for better performance
            if batch_data:
                saved_count = self.db.save_energy_data_batch(batch_data)
                results["energy_stats"] += saved_count
                logger.info(f"Saved {saved_count} energy records for device {device_sn}")
            else:
                logger.warning(f"No valid energy data points found for device {device_sn}")
                
        except Exception as e:
            logger.error(f"Error collecting energy data for device {device_sn}: {str(e)}")
            results["errors"].append(f"Device {device_sn}: {str(e)}")
            # Continue processing - don't re-raise the exception
    
    def _collect_weather_data(self, plant_id: str, results: Dict[str, Any]) -> None:
        """
        Collect weather data for a plant
        
        Args:
            plant_id: Plant ID
            results: Results dictionary to update
        """
        try:
            # Use the api instance for weather data
            weather = self._safe_api_call(self.api.get_weather, plant_id)
            if not weather or weather.get('error'):
                logger.warning(f"No weather data available for plant {plant_id}")
                return
                
            today = datetime.now(get_timezone()).strftime('%Y-%m-%d')
            
            # Extract weather info, format varies based on API response structure
            temp = None
            condition = None
            
            if isinstance(weather, dict):
                temp = weather.get('temperature')
                condition = weather.get('weather')
                
                if temp is not None or condition is not None:
                    result = self.db.save_weather_data(
                        plant_id=plant_id,
                        date=today,
                        temperature=temp,
                        condition=condition
                    )
                    if result:
                        results["weather"] += 1
        except Exception as e:
            logger.error(f"Error collecting weather data for plant {plant_id}: {str(e)}")
            results["errors"].append(f"Weather for plant {plant_id}: {str(e)}")

    def _collect_plants_data(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect plants data from Growatt API
        
        Args:
            results: Results dictionary to update
            
        Returns:
            List of plant data dictionaries
        """
        logger.info("Fetching plant list from API")
        plants = self._safe_api_call(self.api.get_plants)
        
        if not plants:
            logger.error("No plants data returned from API")
            results["errors"].append("No plants data returned from API")
            return []
            
        if not isinstance(plants, list):
            logger.error(f"Unexpected plants data format: {type(plants)}")
            results["errors"].append(f"Unexpected plants data format: {type(plants)}")
            return []
        
        if len(plants) == 0:
            logger.warning("Plants list is empty")
        
        logger.info(f"Successfully retrieved {len(plants)} plants")
        
        plant_store_result = self.db.save_plant_data(plants)
        if plant_store_result:
            results["plants"] = len(plants)
            
        return plants
    
    def _save_to_json(self, data, filename):
        """Save data to a JSON file"""
        if not self.save_to_file:
            return
            
        file_path = os.path.join(self.data_dir, filename)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def _save_to_database(self, data, collection_name):
        """Save data to database - placeholder for future implementation"""
        # Implementation will depend on the database being used
        pass
    
    def _collect_plants(self):
        """Collect plants data from Growatt API"""
        self.api.login(self.username, self.password)
        plants = self.api.get_plants()
        
        if self.save_to_file:
            self._save_to_json(plants, "plants.json")
            
        return plants
    
    def _collect_devices(self, plant_id):
        """Collect devices data for a specific plant"""
        devices = self.api.get_devices_by_plant_list(plant_id)
        
        if self.save_to_file:
            self._save_to_json(devices, f"devices_{plant_id}.json")
            
        return devices
    
    def _collect_energy_stats(self, plant_id, mix_sn, time_period, date_str):
        """Collect energy statistics for a specific device"""
        if time_period == "daily":
            stats = self.api.get_energy_stats_daily(date_str, plant_id, mix_sn)
        elif time_period == "monthly":
            stats = self.api.get_energy_stats_monthly(date_str, plant_id, mix_sn)
        elif time_period == "yearly":
            stats = self.api.get_energy_stats_yearly(date_str, plant_id, mix_sn)
        else:
            stats = {}
            
        return stats
    
    def _generate_test_plants(self):
        """Generate test plant data for testing"""
        return [
            {"id": "1234567", "plantName": "Test Plant 1"},
            {"id": "7654321", "plantName": "Test Plant 2"}
        ]
    
    def _generate_test_devices(self, plant_id):
        """Generate test device data for testing"""
        return {
            "result": 1,
            "obj": {
                "totalCount": 2,
                "mix": [
                    ["TESTMIX1", "TESTMIX1", "0"],
                    ["TESTMIX2", "TESTMIX2", "1"]
                ]
            }
        }
    
    def _generate_test_energy_stats(self, plant_id, mix_sn, time_period, date_str):
        """Generate test energy statistics for testing"""
        return {
            "obj": {
                "etouser": "5.2",
                "elocalLoad": "12.6",
                "charts": {
                    "ppv": [0, 1, 2, 3, 4],
                    "elocalLoad": [1, 2, 3, 4, 5]
                }
            }
        }
    
    def test_data_collection(self, options):
        """Collect test data based on provided options"""
        data_type = options.get('data_type', 'daily')
        test_date = options.get('test_date', date.today().strftime("%Y-%m-%d"))
        dry_run = options.get('dry_run', False)
        output_dir = options.get('output_dir', self.data_dir)
        
        # Generate test data
        plants = self._generate_test_plants()
        
        results = {
            'success': True,
            'plants': [],
            'devices': {},
            'energy_stats': {}
        }
        
        for plant in plants:
            plant_id = plant['id']
            results['plants'].append(plant)
            
            # Get devices for this plant
            devices = self._generate_test_devices(plant_id)
            results['devices'][plant_id] = devices
            
            if not dry_run:
                if devices.get('result') == 1 and 'obj' in devices and 'mix' in devices['obj']:
                    for mix_device in devices['obj']['mix']:
                        mix_sn = mix_device[0]
                        
                        # Get energy stats
                        stats = self._generate_test_energy_stats(
                            plant_id, mix_sn, data_type, test_date
                        )
                        
                        if plant_id not in results['energy_stats']:
                            results['energy_stats'][plant_id] = {}
                        
                        results['energy_stats'][plant_id][mix_sn] = stats
                        
                        # Save to file if requested
                        if self.save_to_file:
                            self._save_to_json(
                                stats,
                                f"test_energy_{data_type}_{plant_id}_{mix_sn}_{test_date}.json"
                            )
        
        return results

# Add standalone functions for scheduled collection

def collect_device_data():
    """
    Collect device data from Growatt API.
    This function is designed to be called by the background scheduler.
    
    Returns:
        Dict[str, Any]: Collection results
    """
    logger.info("Starting scheduled device data collection")
    collector = GrowattDataCollector()
    
    try:
        # Authenticate with API
        if not collector.authenticate():
            logger.error("Failed to authenticate with Growatt API")
            return {"success": False, "message": "Authentication failed"}
        
        # Get plant list
        logger.info("Fetching plant list")
        plants = collector._collect_plants_data({"plants": 0, "errors": []})
        
        if not plants:
            logger.error("No plants data returned from API")
            return {"success": False, "message": "No plants data returned from API"}
        
        # For each plant, collect and store devices
        logger.info(f"Collecting device data for {len(plants)} plants")
        all_devices = []
        results = {
            "plants": len(plants),
            "devices": 0,
            "errors": []
        }
        
        for plant_index, plant in enumerate(plants):
            plant_id = plant.get('id')
            plant_name = plant.get('plantName', 'Unknown')
            
            if not plant_id:
                logger.warning(f"Skipping plant with no ID: {plant}")
                results["errors"].append(f"Missing ID: {plant_name}")
                continue
            
            logger.info(f"Processing plant {plant_index+1}/{len(plants)}: {plant_name} (ID: {plant_id})")
            
            try:
                # Use the api instance to get devices
                logger.info(f"Fetching devices for plant {plant_id}")
                devices_response = collector._safe_api_call(collector.api.get_device_list, plant_id)
                
                # Extract devices from response based on its structure
                device_data = []
                
                # Handle different response formats
                if devices_response is None:
                    logger.warning(f"No response received for plant {plant_id}")
                    device_data = []
                elif isinstance(devices_response, dict):
                    logger.debug(f"Response keys: {list(devices_response.keys())}")
                    
                    # Check for different possible data structures
                    if 'obj' in devices_response and isinstance(devices_response['obj'], dict):
                        if 'datas' in devices_response['obj']:
                            device_data = devices_response['obj']['datas']
                    elif 'datas' in devices_response:
                        device_data = devices_response['datas']
                    elif 'data' in devices_response:
                        if isinstance(devices_response['data'], dict) and 'data' in devices_response['data']:
                            device_data = devices_response['data']['data']
                        elif isinstance(devices_response['data'], list):
                            device_data = devices_response['data']
                elif isinstance(devices_response, list):
                    device_data = devices_response
                
                # Ensure device_data is a list
                if not isinstance(device_data, list):
                    logger.warning(f"Device data is not a list: {type(device_data)}")
                    device_data = []
                
                # Transform device data to match database schema
                transformed_devices = []
                for device in device_data:
                    # Extract device information
                    sn = device.get('sn')
                    if not sn:
                        logger.warning(f"Skipping device with missing serial number: {device}")
                        continue
                    
                    device_type = device.get('deviceType')
                    device_status = device.get('status', 'unknown')
                    last_update = device.get('lastUpdateTime') or datetime.now(get_timezone()).isoformat()
                    
                    # Handle offline status
                    is_offline = device.get('lost') == 'true' or device_status == '0'
                    if is_offline:
                        device_status = 'offline'
                    elif device_status == '1':
                        device_status = 'online'
                    else:
                        device_status = 'unknown'
                    
                    # Handle device alias - ensure it's a string
                    device_alias = device.get('alias') or device.get('deviceName') or f"{device_type} {sn[-4:]}"
                    if not isinstance(device_alias, str):
                        device_alias = str(device_alias)
                    
                    # Convert datetime objects to strings in raw_data for proper JSON serialization
                    raw_data = {}
                    for key, value in device.items():
                        if isinstance(value, datetime):
                            raw_data[key] = value.isoformat()
                        else:
                            raw_data[key] = value
                    
                    # Store current time as ISO format string
                    current_time = datetime.now(get_timezone()).isoformat()
                    
                    # Create the device entry with standardized field names
                    device_entry = {
                        "serial_number": sn,
                        "plant_id": plant_id,
                        "alias": device_alias,
                        "type": device_type,
                        "status": device_status,
                        "last_update_time": last_update,
                        "last_updated": current_time,
                        "raw_data": raw_data
                    }
                    
                    # Convert string last_update_time to datetime if it's a string
                    if isinstance(device_entry["last_update_time"], str):
                        try:
                            # Try to parse the datetime string to ensure it's valid
                            datetime.strptime(device_entry["last_update_time"], "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            # If parsing fails, use current time
                            device_entry["last_update_time"] = current_time
                    
                    transformed_devices.append(device_entry)
                    all_devices.append(device_entry)
                
                logger.info(f"Found {len(transformed_devices)} devices for plant {plant_name} ({plant_id})")
                
                if transformed_devices:
                    try:
                        # Save devices to database with better error handling
                        saved = collector.db.save_device_data(transformed_devices)
                        if saved:
                            logger.info(f"Successfully saved {len(transformed_devices)} devices for plant {plant_name}")
                            results["devices"] += len(transformed_devices)
                        else:
                            logger.error(f"Failed to save devices for plant {plant_name}")
                            results["errors"].append(f"Failed to save devices for plant {plant_name}")
                    except Exception as e:
                        error_msg = f"Error saving devices for plant {plant_name}: {str(e)}"
                        logger.error(error_msg)
                        # Log sample of the problematic data
                        sample_data = [{k: v for k, v in d.items() if k != 'raw_data'} for d in transformed_devices[:2]]
                        logger.error(f"Sample of problematic data: {json.dumps(sample_data, ensure_ascii=False)}")
                        results["errors"].append(error_msg)
                else:
                    logger.warning(f"No devices to save for plant {plant_name}")
            
            except Exception as e:
                error_msg = f"Error collecting devices for plant {plant_id} ({plant_name}): {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Check device status and send notifications if needed
        if all_devices:
            logger.info(f"Checking status of {len(all_devices)} devices for notifications")
            tracker = DeviceStatusTracker()
            notification_results = tracker.check_and_notify_status_changes(all_devices)
            
            # Add notification results to the overall results
            results["notifications"] = notification_results
            
            logger.info(f"Notification check completed: {notification_results.get('offline', 0)} offline notifications, "
                       f"{notification_results.get('online', 0)} online notifications sent")
        
        success = results["devices"] > 0
        message = "Device data collection completed successfully"
        if results["errors"]:
            message = "Device data collection completed with some errors"
            
        logger.info(message)
        return {
            "success": success, 
            "results": results,
            "message": message
        }
    
    except Exception as e:
        logger.error(f"Error in device data collection: {str(e)}", exc_info=True)
        return {"success": False, "message": str(e)}

def collect_plant_data():
    """
    Collect plant data from Growatt API.
    This function is designed to be called by the background scheduler.
    
    Returns:
        Dict[str, Any]: Collection results
    """
    logger.info("Starting scheduled plant data collection")
    collector = GrowattDataCollector()
    
    try:
        # Authenticate with API
        if not collector.authenticate():
            logger.error("Failed to authenticate with Growatt API")
            return {"success": False, "message": "Authentication failed"}
        
        # Collect plants data
        logger.info("Fetching plant list")
        results = {"plants": 0, "errors": []}
        plants = collector._collect_plants_data(results)
        
        if not plants:
            logger.error("No plants data returned from API")
            return {"success": False, "message": "No plants data returned from API"}
        
        # For each plant, collect energy data and weather
        logger.info(f"Collecting additional data for {len(plants)} plants")
        
        for plant_index, plant in enumerate(plants):
            plant_id = plant.get('id')
            plant_name = plant.get('name', 'Unknown')
            
            if not plant_id:
                logger.warning(f"Skipping plant with no ID: {plant}")
                results["errors"].append(f"Missing ID: {plant_name}")
                continue
            
            logger.info(f"Processing plant {plant_index+1}/{len(plants)}: {plant_name} (ID: {plant_id})")
            
            # Collect and store weather data
            try:
                logger.info(f"Collecting weather data for plant {plant_id}")
                collector._collect_weather_data(plant_id, results)
            except Exception as weather_err:
                error_msg = f"Weather data error for plant {plant_id} ({plant_name}): {str(weather_err)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        success = results["plants"] > 0
        message = "Plant data collection completed successfully"
        if results["errors"]:
            message = "Plant data collection completed with some errors"
            
        logger.info(message)
        return {
            "success": success, 
            "results": results,
            "message": message
        }
    
    except Exception as e:
        logger.error(f"Error in plant data collection: {str(e)}", exc_info=True)
        return {"success": False, "message": str(e)}

def collect_and_store_all_data(days_back=7, include_weather=True):
    """
    Standalone function that creates a GrowattDataCollector instance and calls collect_and_store_all_data method.
    This simplifies calling the functionality from command line or import.
    
    Args:
        days_back: Number of days of historical data to collect
        include_weather: Whether to collect weather data
        
    Returns:
        dict: Collection results with success status and statistics
    """
    logger.info("Starting data collection using standalone function")
    collector = GrowattDataCollector()
    return collector.collect_and_store_all_data(days_back=days_back, include_weather=include_weather)

def transform_device_data(device_info, plant_info=None):
    """
    Transform raw device data from API to a structured format
    
    Args:
        device_info (dict): Raw device data from API
        plant_info (dict, optional): Plant information for context
        
    Returns:
        dict: Transformed device data
    """
    device_data = {}
    
    try:
        # Extract core device data
        device_data["serial_number"] = device_info.get("sn", "")
        device_data["plant_id"] = device_info.get("plantId", "")
        device_data["alias"] = device_info.get("alias", "")
        device_data["type"] = device_info.get("deviceType", "")
        
        # Extract device status
        # Status codes: 0 = online/normal, 1 = pending/fault, etc.
        # For lost=True, the device is considered offline regardless of status code
        raw_status = device_info.get("status", "-1")
        is_lost = device_info.get("lost", "true").lower() == "true"
        
        if is_lost or raw_status == "-1":
            device_data["status"] = "offline"
        elif raw_status == "0":
            device_data["status"] = "online"
        else:
            device_data["status"] = "fault"
            
        # Extract last update time
        last_update_time = device_info.get("lastUpdateTime", "")
        device_data["last_update_time"] = last_update_time
        
        # Set the current processing time
        device_data["last_updated"] = datetime.now(get_timezone()).isoformat()
        
        # Store the raw data
        device_data["raw_data"] = device_info
        
        return device_data
    except Exception as e:
        logger.error(f"Error transforming device data: {str(e)}")
        return {}

# For direct script execution
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = collect_and_store_all_data()
    print(result)