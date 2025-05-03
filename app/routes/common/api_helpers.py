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
        
        if not username:
            current_app.logger.error("Missing API credentials: Username not configured in environment variables or .env file")
            return {"success": False, "message": "Missing API credentials: Username not configured", "authenticated": False}
        
        if not password:
            current_app.logger.error("Missing API credentials: Password not configured in environment variables or .env file")
            return {"success": False, "message": "Missing API credentials: Password not configured", "authenticated": False}
        
        current_app.logger.info(f"Attempting to login with username: {username}")
            
        # Perform login with detailed error handling
        try:
            login_result = growatt_api.login(username, password)
            
            # Check login result
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
                    "message": "Authentication failed: Invalid username or password",
                    "authenticated": False
                }
        except ValueError as ve:
            # Handle specific ValueError exceptions from growatt_api.login
            current_app.logger.error(f"API login ValueError: {str(ve)}")
            return {"success": False, "message": f"API Error: {str(ve)}", "authenticated": False}
        except Exception as le:
            # Handle other login exceptions
            current_app.logger.error(f"Login error: {str(le)}")
            return {"success": False, "message": f"Login failed: {str(le)}", "authenticated": False}
    except Exception as e:
        current_app.logger.error(f"Access error: {str(e)}")
        return {"success": False, "message": f"Authentication failed: {str(e)}", "authenticated": False}

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

def get_plant_fault_logs(plant_id: str, date: str = None, device_sn: str = "", page_num: int = 1, device_flag: int = 0, fault_type: int = 1) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch fault logs for a specific plant by its ID from the Growatt API.
    
    Args:
        plant_id (str): The ID of the plant to retrieve fault logs for
        date (str, optional): The date for which to retrieve logs in 'YYYY-MM-DD' format. Defaults to current date.
        device_sn (str, optional): Serial number of a specific device. Empty string for all devices.
        page_num (int, optional): Page number for pagination. Defaults to 1.
        device_flag (int, optional): Flag indicating device type (0=all, 1=inverter, etc). Defaults to 0.
        fault_type (int, optional): Type of fault log to retrieve (1=fault, 2=alarm, etc). Defaults to 1.
    
    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: Plant fault logs data
    """
    try:
        # Ensure login before making API call
        login_status = ensure_login()
        if not login_status.get("success", False):
            current_app.logger.error("Failed to establish session before fetching fault logs")
            return [{"error": "Authentication failed", "code": "AUTH_ERROR", 
                    "ui_message": "Please log in to access fault logs data",
                    "authenticated": False}]
        
        # Validate and convert parameters to appropriate types
        plant_id_str = str(plant_id) if plant_id else ""
        device_sn_str = str(device_sn) if device_sn else ""
        page_num_int = int(page_num) if page_num else 1
        device_flag_int = int(device_flag) if isinstance(device_flag, (int, str)) else 0
        fault_type_int = int(fault_type) if isinstance(fault_type, (int, str)) else 1
        
        # Call the API object's get_fault_logs method with explicit keyword arguments
        try:
            fault_logs = growatt_api.get_fault_logs(
                plantId=plant_id_str,
                date=date,
                device_sn=device_sn_str,
                page_num=page_num_int,
                device_flag=device_flag_int,
                fault_type=fault_type_int
            )
        except TypeError as te:
            current_app.logger.warning(f"TypeError in get_fault_logs with keyword args: {te}")
            # Fallback to original implementation with just plantId if the newer API fails
            fault_logs = growatt_api.get_fault_logs(plant_id_str)
        
        if fault_logs is None:
            current_app.logger.warning(f"No fault logs retrieved for plant ID {plant_id}")
            return []
            
        current_app.logger.info(f"Retrieved fault logs for plant ID {plant_id}")
        return fault_logs
    except TypeError as te:
        current_app.logger.error(f"Type error in get_plant_fault_logs: {str(te)}")
        return [{"error": f"Parameter error: {str(te)}", "code": "TYPE_ERROR", 
                "ui_message": "Invalid parameter format when requesting fault logs.",
                "authenticated": True}]
    except Exception as e:
        current_app.logger.error(f"Error fetching fault logs for plant ID {plant_id}: {e}")
        return [{"error": str(e), "code": "API_ERROR", 
                "ui_message": "An error occurred while fetching fault logs for this plant.",
                "authenticated": False}]

def get_plant_by_id(plant_id: str) -> Union[Dict[str, Any], None]:
    """
    Fetch details for a specific plant by ID from the Growatt API.
    
    Args:
        plant_id (str): The ID of the plant to retrieve
    
    Returns:
        Union[Dict[str, Any], None]: Plant data dictionary or None if not found/error
    """
    try:
        # Ensure login before making API call
        login_status = ensure_login()
        if not login_status.get("success", False):
            current_app.logger.error(f"Failed to establish session before fetching plant ID {plant_id}")
            return {
                "status": "error", 
                "message": "Authentication failed", 
                "code": "AUTH_ERROR", 
                "ui_message": "Please log in to access plant details",
                "authenticated": False
            }
        
        # Convert ID to string if it's not already
        plant_id_str = str(plant_id)
        
        # Call the API object's get_plant method
        try:
            plant_data = growatt_api.get_plant(plantId=plant_id_str)
            
            if not plant_data:
                current_app.logger.warning(f"No data found for plant ID {plant_id}")
                return None
                
            current_app.logger.info(f"Retrieved details for plant ID {plant_id}")
            
            # Add additional fields for consistent API response
            plant_data['authenticated'] = True
            
            # Get status into a consistent format
            status_str = plant_data.get('status')
            if status_str == '1':
                plant_data['status'] = 'active'
            elif status_str == '2':
                plant_data['status'] = 'warning'
            elif status_str == '3':
                plant_data['status'] = 'error'
            elif status_str == '0':
                plant_data['status'] = 'offline'
            
            # Calculate current output and add additional fields
            # (This would need more API calls in a real implementation)
            plant_data['current_output'] = float(plant_data.get('currentPower', 0))
            plant_data['today_energy'] = float(plant_data.get('eToday', 0))
            plant_data['peak_output'] = float(plant_data.get('peakPower', 0))
            
            return plant_data
            
        except ValueError as ve:
            current_app.logger.error(f"ValueError in get_plant for ID {plant_id}: {str(ve)}")
            return {
                "status": "error", 
                "message": f"API Error: {str(ve)}", 
                "code": "API_ERROR", 
                "ui_message": "Unable to retrieve plant details",
                "authenticated": True
            }
    except Exception as e:
        current_app.logger.error(f"Error fetching plant ID {plant_id}: {e}")
        return {
            "status": "error", 
            "message": str(e), 
            "code": "API_ERROR", 
            "ui_message": "An error occurred while fetching plant details",
            "authenticated": False
        }