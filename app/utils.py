import os
from typing import List, Dict, Any, Optional, Union
from app.core.growatt import Growatt
from flask import current_app
import time


# Login credentials from environment variables (with fallbacks for development)
GROWATT_USERNAME = os.environ.get("GROWATT_USERNAME", "enwufttest")
GROWATT_PASSWORD = os.environ.get("GROWATT_PASSWORD", "enwuft1234")
# GROWATT_USERNAME = os.environ.get("GROWATT_USERNAME", "PWA_solar")
# GROWATT_PASSWORD = os.environ.get("GROWATT_PASSWORD", "123456")

api = Growatt()

# Track session status
last_login_time = 0
SESSION_TIMEOUT = 3600  # 1 hour in seconds

def is_session_valid() -> bool:
    """
    Check if the current session is still valid based on timeout.
    
    Returns:
        bool: True if session is valid, False otherwise
    """
    global last_login_time
    return (time.time() - last_login_time) < SESSION_TIMEOUT and hasattr(api, 'is_logged_in') and api.is_logged_in

def ensure_login() -> Dict[str, Any]:
    """
    Ensure the API session is active, logging in if necessary.
    
    Returns:
        Dict[str, Any]: Login status information
    """
    if is_session_valid():
        current_app.logger.debug("Using existing Growatt API session")
        return {"success": True, "message": "Using existing session"}
    else:
        current_app.logger.info("Session expired or not established, logging in again")
        return get_access_api()

def get_access_api() -> Dict[str, Any]:
    """
    Login to the Growatt API using credentials.
    This is the only function that should call the actual login API.
    
    Returns:
        Dict[str, Any]: Raw API response containing login information
    """
    global last_login_time
    try:
        # Perform new login - the only place where login API is called
        login_result = api.login(GROWATT_USERNAME, GROWATT_PASSWORD)
        current_app.logger.info(f"\033[44m\033[97mLogin attempt result: {login_result}\033[0m")
        
        if login_result:
            last_login_time = time.time()
            current_app.logger.info("\033[42m\033[97mSuccessfully logged in to Growatt API\033[0m")
            
            # Return the actual login result from the API
            return {"success": True, "message": "Successfully logged in"}
        else:
            current_app.logger.warning("\033[41m\033[97mLogin failed with invalid credentials\033[0m")
            return {
                "success": False, 
                "message": "Authentication failed: Invalid credentials",
                "code": "INVALID_CREDENTIALS",
                "ui_message": "Your username or password is incorrect. Please check your credentials."
            }
    except Exception as e:
        current_app.logger.error(f"\033[41m\033[97mError logging in to Growatt API: {e}\033[0m")
        
        error_message = str(e)
        error_code = "API_ERROR"
        ui_message = "Could not connect to Growatt service."
        
        if "timeout" in error_message.lower():
            error_code = "TIMEOUT"
            ui_message = "Connection to Growatt timed out. Please try again later."
        elif "connection" in error_message.lower():
            error_code = "CONNECTION_ERROR"
            ui_message = "Could not connect to Growatt servers. Please check your internet connection."
            
        return {
            "success": False, 
            "message": f"Authentication failed: {error_message}",
            "code": error_code,
            "ui_message": ui_message
        }

def get_logout() -> Dict[str, Any]:
    """
    Logout/sign out from the Growatt API.

    Returns:
        Dict[str, Any]: Dictionary containing logout status
    """
    global last_login_time

    try:
        # Only attempt logout if we believe we're logged in
        if hasattr(api, 'is_logged_in') and api.is_logged_in:
            logout_result = api.logout()
            
            if logout_result:
                last_login_time = 0
                current_app.logger.info("\033[42m\033[97mLogged out from Growatt API\033[0m")
                return {"success": True, "message": "Logout successful"}
            else:
                current_app.logger.warning("\033[43m\033[30mLogout attempt returned False\033[0m")
                return {"success": False, "message": "Logout failed: Server rejected request"}
        else:
            # Reset time anyway
            last_login_time = 0
            current_app.logger.info("No active session to log out from")
            return {"success": True, "message": "No active session to log out from", "redirect": "/"}
    except Exception as e:
        current_app.logger.error(f"Error logging out from Growatt API: {e}")
        return {"success": False, "message": f"Logout failed: {str(e)}"}

def get_plants() -> List[Dict[str, Any]]:
    """
    Fetch the list of plants from the Growatt API.

    Returns:
        List[Dict[str, Any]]: List of plant data dictionaries with authentication status
    """
    try:
        # Ensure we have a valid session before making API call
        login_status = ensure_login()
        if not login_status.get("success", False):
            current_app.logger.error("Failed to establish session before fetching plants")
            return [{"error": "Authentication failed", "code": "AUTH_ERROR", 
                 "ui_message": "Please log in to access your plant data",
                 "authenticated": False}]
            
        # Force a fresh login to ensure the session is valid
        if not is_session_valid():
            current_app.logger.info("Session might be invalid, logging in again")
            login_result = get_access_api()
            if not login_result.get("success", False):
                return [{"error": "Authentication failed", "code": "AUTH_ERROR", 
                     "ui_message": "Failed to refresh session. Please log in again.",
                     "authenticated": False}]
            
        # Call the API object's get_plants method, not this function recursively
        plants_data = api.get_plants()
        
        if not plants_data:
            current_app.logger.warning("No plants data retrieved or empty response")
            return [{"error": "No plants found", "code": "NO_PLANTS", 
                 "ui_message": "No solar plants found for this account",
                 "authenticated": True}]  # Changed to True since we confirmed login
            
        if isinstance(plants_data, list):
            for plant in plants_data:
                plant['authenticated'] = True
            current_app.logger.info(f"\033[92mRetrieved {len(plants_data)} plants\033[0m")
            return plants_data
        else:
            current_app.logger.error(f"Unexpected plants data format: {type(plants_data)}")
            return [{"error": "Unexpected response format", "code": "INVALID_FORMAT", 
                 "ui_message": "Received unexpected data format from Growatt",
                 "authenticated": True}]  # Changed to True since we confirmed login
    except Exception as e:
        current_app.logger.error(f"\033[41m\033[97mError in API request get_plants: {e}\033[0m")
        
        # Check if this might be a session issue and try to recover
        if "404" in str(e) or "login" in str(e).lower() or "unauthorized" in str(e).lower():
            current_app.logger.warning("Possible session expiration, attempting to re-authenticate")
            try:
                login_result = get_access_api()
                if login_result.get("success", False):
                    return [{"error": "Authentication failed", "code": "AUTH_ERROR", 
                         "ui_message": "Please log in to access your plant data",
                         "authenticated": False}]
                if login_result.get("success", True):
                    # Retry the API call after successful re-authentication
                    plants_data = api.get_plants()
                    if isinstance(plants_data, list):
                        for plant in plants_data:
                            plant['authenticated'] = True
                        current_app.logger.info(f"\033[92mRetrieved {len(plants_data)} plants after re-authentication\033[0m")
                        return plants_data
            except Exception as retry_error:
                current_app.logger.error(f"Failed to recover session: {retry_error}")
        
        return [{"error": str(e), "code": "API_ERROR", 
             "ui_message": "An error occurred while fetching plant data. Please try logging in again.",
             "authenticated": False}]

def get_plant_ids() -> List[str]:
    """
    Fetch the plant IDs associated with the logged-in user.

    Returns:
        List[str]: List of plant IDs
    """
    
    try:
        # Ensure session is valid
        ensure_login()
        
        plants = api.get_plants()

        if isinstance(plants, list):
            plant_ids = [plant['id'] for plant in plants if 'id' in plant]
            current_app.logger.debug(f"Retrieved {len(plant_ids)} plant IDs")
            return plant_ids

        return []
    except Exception as e:
        current_app.logger.error(f"Error in API request get_plant_ids: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
             "ui_message": "An error occurred while fetching plant IDs.",
             "authenticated": False}]

def get_plant_by_id(plant_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the details of a specific plant by its ID from the Growatt API.

    Args:
        plant_id (str): The ID of the plant to retrieve
        
    Returns:
        Optional[Dict[str, Any]]: Plant data dictionary or None if not found
    """

    try:
        # Ensure session is valid
        ensure_login()
        
        plants = api.get_plants()

        if isinstance(plants, list):
            for plant in plants:
                if plant.get('id') == plant_id:
                    return plant
            
            current_app.logger.warning(f"No plant found with ID: {plant_id}")

        return None
    except Exception as e:
        current_app.logger.error(f"Error in API request get_plant_by_id: {e}")
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
        # Ensure session is valid
        ensure_login()
        
        devices = api.get_device_list(plant_id)
        current_app.logger.debug(f"Retrieved devices for plant ID {plant_id}")
        return devices
    except Exception as e:
        current_app.logger.error(f"Error fetching devices for plant ID {plant_id}: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
             "ui_message": "An error occurred while fetching devices for this plant.",
             "authenticated": False}]

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
        # Ensure session is valid
        ensure_login()
        
        weather_list = api.get_weather(plantId=plant_id or "")

        if plant_id is not None and isinstance(weather_list, list):
            for weather in weather_list:
                if weather.get('id') == plant_id:
                    current_app.logger.debug(f"Retrieved weather for plant ID {plant_id}")
                    return weather
            # If plant_id was specified but not found in results
            return {"warning": f"No weather data found for plant ID {plant_id}", "authenticated": True}

        current_app.logger.debug(f"Retrieved weather data for all plants")
        return weather_list
    except Exception as e:
        current_app.logger.error(f"Error in API request get_weather_list: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
             "ui_message": "An error occurred while fetching weather data.",
             "authenticated": False}]
