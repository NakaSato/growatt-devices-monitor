from app.models.plant import Plant
import random
from datetime import datetime
from app.core.growatt import Growatt
import logging

# Sample data - used as fallback when API connection fails or for development/testing

class PlantService:
    """Service class for managing plant data and operations"""
    
    def __init__(self):
        """Initialize the PlantService"""
        self.plants = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize Growatt API
        from app.core.growatt import GrowattApi
        self.growatt_api = GrowattApi()
        
        # Try to load sample plants
        try:
            # First try to get it from global scope if it's been defined by the frontend scripts
            import builtins
            if hasattr(builtins, 'sample_plants'):
                self.plants = builtins.sample_plants
            else:
                # Fallback to hardcoded sample plants
                self.plants = self._get_sample_plants()
        except Exception as e:
            self.logger.error(f"Error loading sample plants: {str(e)}")
            # Ensure we have at least an empty list
            self.plants = self._get_sample_plants()
    
    def _get_sample_plants(self):
        """Get hardcoded sample plants as fallback"""
        return [
            {
                "id": 10125058,
                "name": "Sample Plant 1",
                "status": "active",
                "currentPower": 15.5,
                "eToday": 75.2,
                "eMonth": 1250.5,
                "eTotal": 42500.8,
                "capacity": 20.0,
                "latitude": 37.7749,
                "longitude": -122.4194,
                "city": "San Francisco",
                "country": "USA"
            },
            {
                "id": 10125059,
                "name": "Sample Plant 2",
                "status": "warning",
                "currentPower": 8.2,
                "eToday": 45.6,
                "eMonth": 950.3,
                "eTotal": 25800.5,
                "capacity": 12.5,
                "latitude": 34.0522,
                "longitude": -118.2437,
                "city": "Los Angeles",
                "country": "USA"
            }
        ]
    
    def get_all_plants(self):
        """Get all plants"""
        try:
            # Try to fetch plants from the Growatt API if user is logged in
            if hasattr(self.growatt_api, 'is_logged_in') and self.growatt_api.is_logged_in:
                api_plants = self.growatt_api.get_plants()
                if api_plants and isinstance(api_plants, list):
                    return api_plants
                else:
                    self.logger.warning("Could not fetch plants from API, using sample data")
            return self.plants
        except Exception as e:
            self.logger.error(f"Error fetching plants from API: {str(e)}")
            return self.plants
    
    def get_plant_detail(self, plant_id):
        """
        Get detailed information for a specific plant.
        
        Attempts to fetch real data from the Growatt API first, 
        falls back to sample data if API call fails.
        """
        try:
            # Try to convert to integer (for sample data) but keep as string for API
            plant_id_str = str(plant_id)
            plant_id_int = int(plant_id) if str(plant_id).isdigit() else None
            
            # First, try to use the api_helpers function to get plant data
            from app.routes.common.api_helpers import get_plant_by_id
            
            api_plant = None
            try:
                api_plant = get_plant_by_id(plant_id_str)
                # If api_plant is an error response or None, we'll fall back to other methods
                if api_plant and isinstance(api_plant, dict) and not api_plant.get('status') == 'error':
                    # Transform API response to match expected format if needed
                    plant_data = self._normalize_plant_data(api_plant)
                    
                    # Add power distribution data
                    self._add_power_distribution(plant_data)
                    return plant_data
            except Exception as api_error:
                self.logger.error(f"Error fetching plant {plant_id} using API helper: {str(api_error)}")
                # Continue to direct API call if helper fails
                
            # Try direct API call if the helper didn't work
            if hasattr(self.growatt_api, 'is_logged_in') and self.growatt_api.is_logged_in:
                try:
                    api_plant = self.growatt_api.get_plant(plantId=plant_id_str)
                    if api_plant:
                        # Transform API response to match expected format
                        plant_data = {
                            'id': api_plant.get('id'),
                            'name': api_plant.get('plantName', 'Unknown Plant'),
                            'status': self._determine_plant_status(api_plant),
                            'latitude': float(api_plant.get('lat', 0)),
                            'longitude': float(api_plant.get('lng', 0)),
                            'capacity': float(api_plant.get('nominalPower', 0)),
                            'current_output': self._get_current_output(api_plant),
                            'today_energy': self._get_today_energy(api_plant),
                            'peak_output': self._get_peak_output(api_plant),
                            'install_date': api_plant.get('creatDate'),
                            'location': f"{api_plant.get('city', '')}, {api_plant.get('country', '')}".strip(', '),
                            'country': api_plant.get('country'),
                            'city': api_plant.get('city'),
                            'co2_avoided': float(api_plant.get('co2', 0)),
                            'total_energy': float(api_plant.get('eTotal', 0)),
                            'plant_type': api_plant.get('plantType'),
                            'timezone': api_plant.get('timezone'),
                        }
                        
                        # Add power distribution data
                        self._add_power_distribution(plant_data)
                        return plant_data
                except Exception as api_error:
                    self.logger.error(f"Error fetching plant {plant_id} from direct API: {str(api_error)}")
                    # Continue to fallback data if API fails
            
            # Fallback to sample data if API calls fail or user not logged in
            if plant_id_int is not None:
                for plant in self.plants:
                    if plant['id'] == plant_id_int:
                        plant_data = plant.copy()
                        self._add_power_distribution(plant_data)
                        return plant_data
                
                # If the specific plant ID wasn't found in sample data but we need a fallback,
                # use the first sample plant but update its ID
                if self.plants and len(self.plants) > 0:
                    self.logger.warning(f"Using first sample plant as fallback for ID {plant_id}")
                    plant_data = self.plants[0].copy()
                    plant_data['id'] = plant_id_int  # Use the requested ID
                    plant_data['name'] = f"Plant {plant_id}"  # Update name
                    self._add_power_distribution(plant_data)
                    return plant_data
            
            return None
        except Exception as e:
            self.logger.error(f"Error in get_plant_detail: {str(e)}")
            return None
    
    def _determine_plant_status(self, api_plant):
        """Determine plant status based on API data"""
        # Logic to determine status based on API data
        # This is a simplified example - you may need more complex logic
        if api_plant.get('status') == '1':
            return 'active'
        elif api_plant.get('status') == '2':
            return 'warning'
        elif api_plant.get('status') == '3':
            return 'error'
        elif api_plant.get('status') == '0':
            return 'offline'
        else:
            # If we can't determine status, check if there's recent energy production
            if float(api_plant.get('eToday', 0)) > 0:
                return 'active'
            return 'offline'
    
    def _get_current_output(self, api_plant):
        """Get current power output from API data"""
        # Implement logic to extract current output
        # This may require another API call in a real implementation
        current_output = float(api_plant.get('currentPower', 0))
        return current_output
    
    def _get_today_energy(self, api_plant):
        """Get today's energy production from API data"""
        today_energy = float(api_plant.get('eToday', 0))
        return today_energy
    
    def _get_peak_output(self, api_plant):
        """Get peak power output from API data"""
        # This might require additional API calls in a real implementation
        peak_output = float(api_plant.get('peakPower', 0))
        return peak_output
    
    def _add_power_distribution(self, plant_data):
        """Add power distribution data to plant data"""
        current_output = plant_data.get('current_output', 0)
        
        # Add power distribution data if the plant is active
        if plant_data.get('status') in ['active', 'warning'] and current_output > 0:
            # Calculate power values for different destinations
            self_consumption = round(current_output * 0.4, 1)  # 40% for self consumption
            power_to_grid = round(current_output * 0.45, 1)    # 45% exported to grid
            power_to_battery = round(current_output * 0.15, 1) # 15% to battery
            
            # Add power values to plant data
            plant_data['power_self_consumption'] = self_consumption
            plant_data['power_to_grid'] = power_to_grid
            plant_data['power_to_battery'] = power_to_battery
            plant_data['last_update_time'] = datetime.now().isoformat()
        else:
            # If the plant is not active, set all power values to 0
            plant_data['power_self_consumption'] = 0
            plant_data['power_to_grid'] = 0
            plant_data['power_to_battery'] = 0
            plant_data['last_update_time'] = datetime.now().isoformat()
    
    def get_maps_plants(self):
        """Get all plants formatted for map display"""
        plants = []
        all_plants = self.get_all_plants()
        
        for plant_data in all_plants:
            # Handle both API response format and sample data format
            if isinstance(plant_data, dict):
                # Convert API response format to Plant object
                plant_obj = Plant.from_dict(self._normalize_plant_data(plant_data))
                plants.append(plant_obj)
            else:
                # Already a Plant object
                plants.append(plant_data)
        
        return plants
    
    def _normalize_plant_data(self, plant_data):
        """Normalize plant data from API to match the expected format"""
        # This handles differences between API response and sample data format
        normalized = {}
        
        # Map fields from API response to expected format
        normalized['id'] = plant_data.get('id') or plant_data.get('plantId')
        normalized['name'] = plant_data.get('name') or plant_data.get('plantName', 'Unknown Plant')
        normalized['status'] = plant_data.get('status', 'offline')
        
        # Handle coordinates
        normalized['latitude'] = plant_data.get('latitude') or float(plant_data.get('lat', 0))
        normalized['longitude'] = plant_data.get('longitude') or float(plant_data.get('lng', 0))
        
        # Handle power/energy data
        normalized['capacity'] = plant_data.get('capacity') or float(plant_data.get('nominalPower', 0))
        normalized['current_output'] = plant_data.get('current_output') or float(plant_data.get('currentPower', 0))
        normalized['today_energy'] = plant_data.get('today_energy') or float(plant_data.get('eToday', 0))
        normalized['peak_output'] = plant_data.get('peak_output') or float(plant_data.get('peakPower', 0))
        
        # Handle dates and location
        normalized['install_date'] = plant_data.get('install_date') or plant_data.get('creatDate')
        normalized['location'] = plant_data.get('location') or f"{plant_data.get('city', '')}, {plant_data.get('country', '')}".strip(', ')
        
        return normalized
    
    def get_plant_by_id(self, plant_id):
        """Get a plant by ID"""
        plant_data = self.get_plant_detail(plant_id)
        if plant_data:
            normalized_data = self._normalize_plant_data(plant_data)
            return Plant.from_dict(normalized_data)
        return None
    
    def get_plant_status_counts(self):
        """Get counts of plants by status"""
        all_plants = self.get_all_plants()
        
        # If all_plants is in API format, normalize the data first
        normalized_plants = []
        for plant in all_plants:
            if isinstance(plant, dict):
                if 'status' not in plant and 'plantStatus' in plant:
                    # Map API status values to our status values
                    if plant.get('plantStatus') == '1':
                        plant['status'] = 'active'
                    elif plant.get('plantStatus') == '2':
                        plant['status'] = 'warning'
                    elif plant.get('plantStatus') == '3':
                        plant['status'] = 'error'
                    else:
                        plant['status'] = 'offline'
                normalized_plants.append(plant)
        
        # Count plants by status
        if normalized_plants:
            all_plants = normalized_plants
            
        total = len(all_plants)
        active = sum(1 for plant in all_plants if plant.get('status') == 'active')
        warning = sum(1 for plant in all_plants if plant.get('status') == 'warning')
        error = sum(1 for plant in all_plants if plant.get('status') == 'error')
        
        return total, active, warning, error

# Keep the original functions for backwards compatibility
def get_maps_plants():
    """Get all plants (legacy function)"""
    service = PlantService()
    return service.get_maps_plants()

def get_plant_by_id(plant_id):
    """Get a plant by ID (legacy function)"""
    service = PlantService()
    return service.get_plant_by_id(plant_id)

def get_plant_status_counts():
    """Get counts of plants by status (legacy function)"""
    service = PlantService()
    return service.get_plant_status_counts()
