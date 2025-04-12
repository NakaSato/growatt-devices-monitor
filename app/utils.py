import os
from typing import List, Dict, Any, Optional, Union
from app.core.growatt import Growatt
from flask import current_app

# Initialize the Growatt API client
api = Growatt()

# Login credentials from environment variables (with fallbacks for development)
GROWATT_USERNAME = os.environ.get("GROWATT_USERNAME", "enwufttest")
GROWATT_PASSWORD = os.environ.get("GROWATT_PASSWORD", "enwuft1234")

def get_access() -> bool:
    """
    Login to the Growatt API using credentials.
    
    Returns:
        bool: True if login was successful, False otherwise.
    """
    try:
        api.login(GROWATT_USERNAME, GROWATT_PASSWORD)
        current_app.logger.info("Successfully logged in to Growatt API")
        
        token = api.token if hasattr(api, 'token') else None
        if token:
            current_app.logger.debug(f"Authorization token retrieved")
        return True
    except Exception as e:
        current_app.logger.error(f"Error logging in to Growatt API: {e}")
        return False

def get_logout() -> bool:
    """
    Logout/sign out from the Growatt API.
    
    Returns:
        bool: True if logout was successful, False otherwise.
    """
    try:
        api.logout()
        current_app.logger.info("Successfully logged out from Growatt API")
        return True
    except Exception as e:
        current_app.logger.error(f"Error logging out from Growatt API: {e}")
        return False

def get_plants() -> List[Dict[str, Any]]:
    """
    Fetch the list of plants from the Growatt API.
    
    Returns:
        List[Dict[str, Any]]: List of plant data dictionaries
    """
    try:
        plants = api.get_plants()
        current_app.logger.debug(f"Retrieved {len(plants)} plants")
        return plants
    except Exception as e:
        current_app.logger.error(f"Error fetching plants: {e}")
        return []

def get_plant_ids() -> List[str]:
    """
    Fetch the plant IDs associated with the logged-in user.
    
    Returns:
        List[str]: List of plant IDs
    """
    try:
        plants = api.get_plants()
        plant_ids = [plant['id'] for plant in plants]
        current_app.logger.debug(f"Retrieved {len(plant_ids)} plant IDs")
        return plant_ids
    except Exception as e:
        current_app.logger.error(f"Error fetching plant IDs: {e}")
        return []

def get_plant_by_id(plant_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the details of a specific plant by its ID from the Growatt API.
    
    Args:
        plant_id (str): The ID of the plant to retrieve
        
    Returns:
        Optional[Dict[str, Any]]: Plant data dictionary or None if not found
    """
    try:
        plants = api.get_plants()
        for plant in plants:
            if plant['id'] == plant_id:
                return plant
        current_app.logger.warning(f"No plant found with ID: {plant_id}")
        return None
    except Exception as e:
        current_app.logger.error(f"Error fetching plant by ID {plant_id}: {e}")
        return None

def get_devices_for_plant(plant_id: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch the list of devices for a specific plant by its ID from the Growatt API.
    
    Args:
        plant_id (str): The ID of the plant to retrieve devices for
        
    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: Devices data
    """
    try:
        devices = api.get_device_list(plant_id)
        current_app.logger.debug(f"Retrieved devices for plant ID {plant_id}")
        return devices
    except Exception as e:
        current_app.logger.error(f"Error fetching devices for plant ID {plant_id}: {e}")
        return []

def get_weather_list(plant_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch weather data for a specific plant or all plants.
    
    Args:
        plant_id (Optional[str]): The ID of the plant to retrieve weather for,
                                or None to get all weather data
        
    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: Weather data
    """
    try:
        weather_list = api.get_weather(plantId=plant_id or "")
        
        if plant_id is not None:
            for weather in weather_list:
                if weather['id'] == plant_id:
                    current_app.logger.debug(f"Retrieved weather for plant ID {plant_id}")
                    return weather
        
        current_app.logger.debug(f"Retrieved weather data for all plants")
        return weather_list
    except Exception as e:
        current_app.logger.error(f"Error fetching weather data: {e}")
        return []