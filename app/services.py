from growatt import Growatt

# Initialize the Growatt API client
api = Growatt()

# Login credentials (use environment variables for security)
GROWATT_USERNAME = "PWA_solar"
GROWATT_PASSWORD = "123456"

# Login to Growatt API
api.login(GROWATT_USERNAME, GROWATT_PASSWORD)

def get_plants():
    """
    Fetch the list of plants from the Growatt API.
    """
    return api.get_plants()

def get_plant_ids():
    """
    Fetch the plant IDs associated with the logged-in user.
    """
    try:
        plants = api.get_plants()
        plant_ids = [plant['id'] for plant in plants]
        return plant_ids
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching plant IDs: {e}")
        return []

def get_plant_by_id(plant_id):
    """
    Fetch the details of a specific plant by its ID from the Growatt API.
    """
    try:
        plants = api.get_plants()
        for plant in plants:
            if plant['id'] == plant_id:
                return plant
        return None  # Return None if no plant with the given ID is found
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching plant by ID: {e}")
        return None
    
def get_devices_for_plant(plant_id):
    """
    Fetch the list of devices for a specific plant by its ID from the Growatt API.
    """
    try:
        devices = api.get_device_list(plant_id)
        return devices
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching devices for plant ID {plant_id}: {e}")
        return []