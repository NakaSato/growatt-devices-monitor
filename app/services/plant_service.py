from app.models.plant import Plant
import random
from datetime import datetime

# Sample data - in a real application, this would come from a database
sample_plants = [
    {
        'id': 1,
        'name': 'Bangkok Solar Farm',
        'status': 'active',
        'latitude': 13.7563,
        'longitude': 100.5018,
        'capacity': 500,
        'current_output': 375.5,
        'today_energy': 1820.6,
        'peak_output': 485.2,
        'install_date': '2020-05-15',
        'location': 'Bangkok'
    },
    {
        'id': 2,
        'name': 'Chiang Mai Solar Array',
        'status': 'active',
        'latitude': 18.7883,
        'longitude': 98.9853,
        'capacity': 350,
        'current_output': 290.8,
        'today_energy': 1425.3,
        'peak_output': 330.7,
        'install_date': '2021-02-10',
        'location': 'Chiang Mai'
    },
    {
        'id': 3,
        'name': 'Phuket Solar Plant',
        'status': 'warning',
        'latitude': 7.9519,
        'longitude': 98.3381,
        'capacity': 250,
        'current_output': 180.4,
        'today_energy': 950.2,
        'peak_output': 230.5,
        'install_date': '2019-11-30',
        'location': 'Phuket'
    },
    {
        'id': 4,
        'name': 'Pattaya Energy Center',
        'status': 'error',
        'latitude': 12.9236,
        'longitude': 100.8824,
        'capacity': 400,
        'current_output': 0,
        'today_energy': 650.7,
        'peak_output': 382.1,
        'install_date': '2018-07-22',
        'location': 'Pattaya'
    },
    {
        'id': 5,
        'name': 'Khon Kaen Solar Park',
        'status': 'active',
        'latitude': 16.4419,
        'longitude': 102.8360,
        'capacity': 300,
        'current_output': 275.3,
        'today_energy': 1325.9,
        'peak_output': 295.6,
        'install_date': '2022-01-05',
        'location': 'Khon Kaen'
    },
    {
        'id': 6,
        'name': 'Ayutthaya Power Plant',
        'status': 'offline',
        'latitude': 14.3692,
        'longitude': 100.5876,
        'capacity': 280,
        'current_output': 0,
        'today_energy': 0,
        'peak_output': 0,
        'install_date': '2021-06-18',
        'location': 'Ayutthaya'
    },
    {
        'id': 7,
        'name': 'Krabi Solar Field',
        'status': 'active',
        'latitude': 8.0863,
        'longitude': 98.9063,
        'capacity': 220,
        'current_output': 192.5,
        'today_energy': 986.3,
        'peak_output': 215.8,
        'install_date': '2020-12-12',
        'location': 'Krabi'
    },
    {
        'id': 8,
        'name': 'Udon Thani Energy',
        'status': 'active',
        'latitude': 17.4072,
        'longitude': 102.7882,
        'capacity': 320,
        'current_output': 280.6,
        'today_energy': 1405.2,
        'peak_output': 315.3,
        'install_date': '2019-04-08',
        'location': 'Udon Thani'
    },
    {
        'id': 9,
        'name': 'Chonburi Solar Grid',
        'status': 'warning',
        'latitude': 13.3611,
        'longitude': 100.9847,
        'capacity': 420,
        'current_output': 320.4,
        'today_energy': 1520.7,
        'peak_output': 395.2,
        'install_date': '2018-09-17',
        'location': 'Chonburi'
    },
    {
        'id': 10,
        'name': 'Nakhon Ratchasima Farm',
        'status': 'active',
        'latitude': 14.9798,
        'longitude': 102.0931,
        'capacity': 380,
        'current_output': 345.8,
        'today_energy': 1680.5,
        'peak_output': 375.7,
        'install_date': '2022-03-25',
        'location': 'Nakhon Ratchasima'
    },
    {
        'id': 11,
        'name': 'Songkhla Solar Array',
        'status': 'active',
        'latitude': 7.1756,
        'longitude': 100.6142,
        'capacity': 290,
        'current_output': 262.3,
        'today_energy': 1285.9,
        'peak_output': 284.6,
        'install_date': '2021-08-30',
        'location': 'Songkhla'
    },
    {
        'id': 12,
        'name': 'Surat Thani Energy',
        'status': 'maintenance',
        'latitude': 9.1348,
        'longitude': 99.3217,
        'capacity': 260,
        'current_output': 120.5,
        'today_energy': 620.3,
        'peak_output': 150.8,
        'install_date': '2019-10-15',
        'location': 'Surat Thani'
    }
]

class PlantService:
    """Service class for managing plant data and operations"""
    
    def __init__(self):
        """Initialize the PlantService"""
        self.plants = sample_plants
    
    def get_all_plants(self):
        """Get all plants"""
        return self.plants
    
    def get_plant_detail(self, plant_id):
        """Get detailed information for a specific plant"""
        try:
            plant_id = int(plant_id)  # Convert to integer if it's a string
            for plant in self.plants:
                if plant['id'] == plant_id:
                    # Add additional power distribution data for the chart
                    plant_data = plant.copy()
                    
                    # Generate random power distribution data
                    total_capacity = plant_data['capacity']
                    current_output = plant_data['current_output']
                    
                    # Add power distribution data if the plant is active
                    if plant_data['status'] in ['active', 'warning'] and current_output > 0:
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
                    
                    return plant_data
            return None
        except Exception as e:
            print(f"Error getting plant detail: {str(e)}")
            return None
    
    def get_maps_plants(self):
        """Get all plants formatted for map display"""
        plants = []
        for plant_data in self.plants:
            plants.append(Plant.from_dict(plant_data))
        return plants
    
    def get_plant_by_id(self, plant_id):
        """Get a plant by ID"""
        for plant_data in self.plants:
            if plant_data['id'] == plant_id:
                return Plant.from_dict(plant_data)
        return None
    
    def get_plant_status_counts(self):
        """Get counts of plants by status"""
        total = len(self.plants)
        active = sum(1 for plant in self.plants if plant['status'] == 'active')
        warning = sum(1 for plant in self.plants if plant['status'] == 'warning')
        error = sum(1 for plant in self.plants if plant['status'] == 'error')
        
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
