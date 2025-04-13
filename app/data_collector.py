import logging
from typing import Dict, Any
from datetime import datetime, timedelta

# Remove Flask imports that are causing problems
# from flask import current_app, Flask

from app.core.growatt import (
    get_plants, get_devices_for_plant, get_weather_list,
    api
)
from app.database import DatabaseConnector

logger = logging.getLogger(__name__)

class GrowattDataCollector:
    """Collects data from Growatt API and stores it in the database"""
    
    def __init__(self):
        """Initialize the data collector with database connector"""
        self.db = DatabaseConnector()
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with the Growatt API"""
        try:
            # Modify the get_access_api to not require Flask context
            from app.core.growatt import api, GROWATT_USERNAME, GROWATT_PASSWORD
            
            # Directly use the API login method instead of get_access_api
            login_result = api.login(GROWATT_USERNAME, GROWATT_PASSWORD)
            
            if not login_result:
                logger.error("Authentication failed: Invalid credentials or API error")
                return False
                
            self.authenticated = True
            logger.info("Successfully authenticated with Growatt API")
            return True
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def _safe_api_call(self, func, *args, **kwargs):
        """Safely call API functions that might require Flask app context"""
        try:
            # Try direct call first, since we're not requiring Flask context
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in API call: {str(e)}")
            raise
    
    def collect_and_store_all_data(self) -> Dict[str, Any]:
        """Collect and store all data from Growatt API"""
        if not self.authenticated and not self.authenticate():
            return {"success": False, "message": "Authentication failed"}
            
        results = {
            "plants": 0,
            "devices": 0,
            "energy_stats": 0,
            "weather": 0,
            "errors": []
        }
        
        try:
            # Collect and store plant data using safe API call
            plants = self._safe_api_call(get_plants)
            if not plants or not isinstance(plants, list):
                return {"success": False, "message": "Failed to retrieve plants"}
                
            plant_store_result = self.db.save_plant_data(plants)
            if plant_store_result:
                results["plants"] = len(plants)
            
            # For each plant, collect and store devices, energy data, and weather
            for plant in plants:
                plant_id = plant.get('id')
                if not plant_id:
                    continue
                
                # Collect and store device data with safe API call
                devices = self._safe_api_call(get_devices_for_plant, plant_id)
                if isinstance(devices, list):
                    device_data = devices
                elif isinstance(devices, dict) and 'datas' in devices:
                    device_data = devices.get('datas', [])
                else:
                    device_data = []
                
                # Transform device data to match database schema
                transformed_devices = []
                for device in device_data:
                    transformed_devices.append({
                        "serial_number": device.get('sn'),
                        "plant_id": plant_id,
                        "alias": device.get('alias', ''),
                        "type": device.get('deviceTypeName', ''),
                        "status": device.get('status', '')
                    })
                if transformed_devices:
                    device_store_result = self.db.save_device_data(transformed_devices)
                    if device_store_result:
                        results["devices"] += len(transformed_devices)
                
                # Collect energy data for each device
                for device in device_data:
                    sn = device.get('sn')
                    if not sn:
                        continue
                    
                    # Get daily energy data for the past 7 days
                    self._collect_device_energy_data(plant_id, sn, results)
                
                # Collect and store weather data
                weather = self._safe_api_call(get_weather_list, plant_id)
                if weather and not weather.get('error'):
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    # Extract weather info, format varies based on API response structure
                    temp = None
                    condition = None
                    
                    if isinstance(weather, dict):
                        temp = weather.get('temperature')
                        condition = weather.get('weather')
                    # Collect and store weather data
                    if isinstance(weather, dict):
                        if temp is not None or condition is not None:
                            result = self.db.save_weather_data(
                                plant_id=plant_id,
                                date=today,
                                temperature=temp,
                                condition=condition
                            )
                            if result:
                                results["weather"] += 1
                
                return {"success": True, "results": results}
        except Exception as e:
            logger.error(f"Error collecting data: {str(e)}")
            results["errors"].append(str(e))
            return {"success": False, "message": str(e), "partial_results": results}
    
    def _collect_device_energy_data(self, plant_id: str, device_sn: str, results: Dict[str, Any]) -> None:
        """Collect energy data for a specific device"""
        try:
            # Get data for the last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Format dates for API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Call Growatt API to get energy data
            energy_data = self._safe_api_call(api.get_energy_stats,
                                              plant_id=plant_id,
                                              device_sn=device_sn,
                                              start_date=start_date_str,
                                              end_date=end_date_str)
            if not energy_data:
                logger.warning(f"No energy data returned for device {device_sn}")
                return
                
            # Process energy data
            if isinstance(energy_data, dict) and 'data' in energy_data:
                data_points = energy_data.get('data', [])
                
                for data_point in data_points:
                    date = data_point.get('date')
                    energy = data_point.get('energy', 0.0)
                    peak_power = data_point.get('peak_power')
                    
                    if date and energy is not None:
                        result = self.db.save_energy_data(
                            plant_id=plant_id,
                            mix_sn=device_sn,
                            date=date,
                            daily_energy=float(energy),
                            peak_power=peak_power
                        )
                        if result:
                            results["energy_stats"] += 1
        except Exception as e:
            logger.error(f"Error collecting energy data for device {device_sn}: {str(e)}")
            results["errors"].append(f"Device {device_sn}: {str(e)}")
