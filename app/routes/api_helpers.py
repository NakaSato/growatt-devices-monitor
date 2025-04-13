import time
from typing import Union, Dict, Any, List

from flask import session, current_app

# Global variables to manage session state
last_login_time = 0
# Session timeout in seconds (15 minutes)
SESSION_TIMEOUT = 15 * 60

# Keep reference to the Growatt API instance
growatt_api = None

def initialize(api_instance):
    """
    Initialize this module with the Growatt API instance.
    
    Args:
        api_instance: The Growatt API instance
    """
    global growatt_api
    growatt_api = api_instance

def is_session_valid() -> bool:
    """
    Check if the current session is valid based on timeout.
    
    Returns:
        bool: True if session is valid, False otherwise
    """
    global last_login_time
    
    # If the API isn't logged in yet, return False
    if not hasattr(growatt_api, 'is_logged_in') or not growatt_api.is_logged_in:
        return False
        
    # Check if session has timed out
    current_time = time.time()
    if current_time - last_login_time > SESSION_TIMEOUT:
        current_app.logger.info("Session has timed out")
        return False
        
    return True

def ensure_login() -> Dict[str, Any]:
    """
    Ensure the API session is active by checking validity and logging in if needed.
    
    Returns:
        Dict[str, Any]: Login status information
    """
    if not is_session_valid():
        current_app.logger.info("Session not valid, performing fresh login")
        return get_access_api()
    
    current_app.logger.debug("Using existing session")
    return {"success": True, "message": "Using existing session"}

def get_access_api() -> Dict[str, Any]:
    """
    Login to the Growatt API using credentials and store state in session.
    
    Returns:
        Dict[str, Any]: Result dictionary with success status and data
    """
    global last_login_time
    
    try:
        # Get credentials from environment variables
        username = current_app.config.get("GROWATT_USERNAME")
        password = current_app.config.get("GROWATT_PASSWORD")
        
        if not username or not password:
            return {"success": False, "message": "Missing API credentials", "authenticated": False}
            
        # Perform login
        login_result = growatt_api.login(username, password)
        
        if login_result:
            # Update last login time
            last_login_time = time.time()
            # Store authentication state in session
            session['growatt_authenticated'] = True
            session['growatt_login_time'] = time.time()
            current_app.logger.info("Successfully logged in to Growatt API")
            return {"success": True, "message": "Successfully logged in", "authenticated": True}
        else:
            # Clear session on failed login
            if 'growatt_authenticated' in session:
                session.pop('growatt_authenticated')
            if 'growatt_login_time' in session:
                session.pop('growatt_login_time')
            current_app.logger.warning("Login failed with invalid credentials")
            return {
                "success": False, 
                "message": "Authentication failed: Invalid credentials",
                "authenticated": False
            }
    except Exception as e:
        current_app.logger.error(f"Access error: {str(e)}")
        return {"success": False, "message": str(e), "authenticated": False}

def get_plants() -> List[Dict[str, Any]]:
    """
    Fetch the list of plants from the Growatt API.
    
    Returns:
        List[Dict[str, Any]]: List of plant data dictionaries with authentication status
    """
    try:
        # Ensure login before making API call
        login_status = ensure_login()
        if not login_status.get("success", False):
            current_app.logger.error("Failed to establish session before fetching plants")
            return [{"error": "Authentication failed", "code": "AUTH_ERROR", 
                    "ui_message": "Please log in to access your plant data",
                    "authenticated": False}]
        
        # Call the API object's get_plants method
        plants_data = growatt_api.get_plants()
        
        if not plants_data:
            current_app.logger.warning("No plants data retrieved or empty response")
            return [{"error": "No plants found", "code": "NO_PLANTS", 
                    "ui_message": "No solar plants found for this account",
                    "authenticated": True}]
            
        if isinstance(plants_data, list):
            for plant in plants_data:
                plant['authenticated'] = True
            current_app.logger.info(f"Retrieved {len(plants_data)} plants")
            return plants_data
        else:
            current_app.logger.error(f"Unexpected plants data format: {type(plants_data)}")
            return [{"error": "Unexpected response format", "code": "INVALID_FORMAT", 
                    "ui_message": "Received unexpected data format from Growatt",
                    "authenticated": True}]
    except Exception as e:
        current_app.logger.error(f"Error in API request get_plants: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
                "ui_message": "An error occurred while fetching plant data. Please try logging in again.",
                "authenticated": False}]

def get_logout() -> Dict[str, Any]:
    """
    Logout/sign out from the Growatt API.
            
    Returns:
        Dict[str, Any]: Dictionary containing logout status
    """
    try:
        # Only attempt logout if we believe we're logged in
        if hasattr(growatt_api, 'is_logged_in') and growatt_api.is_logged_in:
            logout_result = growatt_api.logout()
            
            if logout_result:
                current_app.logger.info("Logged out from Growatt API")
                return {"success": True, "message": "Logout successful"}
            else:
                current_app.logger.warning("Logout attempt returned False")
                return {"success": False, "message": "Logout failed: Server rejected request"}
        else:
            current_app.logger.info("No active session to log out from")
            return {"success": True, "message": "No active session to log out from", "redirect": "/"}
    except Exception as e:
        current_app.logger.error(f"Error logging out from Growatt API: {e}")
        return {"success": False, "message": f"Logout failed: {str(e)}"}

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
        devices = growatt_api.get_device_list(plant_id)
        current_app.logger.debug(f"Retrieved devices for plant ID {plant_id}")
        return devices
    except Exception as e:
        current_app.logger.error(f"Error fetching devices for plant ID {plant_id}: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
                "ui_message": "An error occurred while fetching devices for this plant.",
                "authenticated": False}]

def get_weather_list(plant_id: str = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
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
        weather_list = growatt_api.get_weather(plant_id or "")
        current_app.logger.debug(f"Retrieved weather data for plant ID {plant_id or 'all'}")
        return weather_list
    except Exception as e:
        current_app.logger.error(f"Error in API request get_weather_list: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
                "ui_message": "An error occurred while fetching weather data.",
                "authenticated": False}]
