import json
import logging
import time
from typing import Tuple, Union, Dict, Any, List

from flask import Blueprint, jsonify, request, make_response, Response, current_app, session
from werkzeug.wrappers import Response as WerkzeugResponse

# Import Growatt class directly instead of utility functions
from app.core.growatt import Growatt

from app.views.templates import (
    render_index, render_plants, render_devices,
    render_weather, render_error_404
)
# Import the prediction routes
from app.routes.prediction_routes import prediction_routes
# Import the data routes
from app.routes.data_routes import data_routes
from flask import render_template

# Create a Blueprint for routes
api_blueprint = Blueprint('api', __name__)

# Register the prediction routes blueprint
api_blueprint.register_blueprint(prediction_routes)
# Register the data routes blueprint
api_blueprint.register_blueprint(data_routes)

# Initialize Growatt API instance
growatt_api = Growatt()
# Track when the last login occurred
last_login_time = 0
# Session timeout in seconds (15 minutes)
SESSION_TIMEOUT = 15 * 60

# ===== Utility Functions =====

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


# ===== Basic Page Routes =====
@api_blueprint.route('/', methods=['GET'])
def index() -> str:
    """
    Index route to render the homepage.
    
    Returns:
        str: Rendered HTML template
    """
    try:
        return render_index()
    except Exception as e:
        current_app.logger.error(f"Error rendering index page: {str(e)}")
        # Fallback to direct template rendering
        return render_template('index.html')

@api_blueprint.errorhandler(404)
def page_not_found(e):
    """
    Handle 404 errors with a custom template.
    
    Args:
        e: The error that occurred
        
    Returns:
        tuple: Rendered error template and 404 status code
    """
    current_app.logger.warning(f"404 error: {request.path}")
    return render_error_404(), 404

@api_blueprint.route('/plants', methods=['GET'])
def plants_page() -> Union[str, Tuple[str, int]]:
    """
    Get the list of plants associated with the logged-in user.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        plants_data = get_plants()
        # Check if plants_data is None or empty or contains an error
        if not plants_data:
            current_app.logger.warning("No plants found for the user.")
            return render_plants([])  # Pass empty list instead of returning 404
        
        # Handle the case where plants_data is not a list
        if not isinstance(plants_data, list):
            current_app.logger.error("Invalid data format for plants.")
            return render_plants([])  # Pass empty list
        
        # Check if error is in the first item
        if len(plants_data) > 0 and 'error' in plants_data[0]:
            error_message = plants_data[0].get('error', 'Unknown error occurred fetching plant data')
            current_app.logger.error(f"API returned error: {error_message}")
            return render_plants([])  # Pass empty list with error message
            
        return render_plants(plants_data)
    except Exception as e:
        current_app.logger.error(f"Error in plants_page: {str(e)}")
        return render_plants([])  # Pass empty list instead of returning 404

@api_blueprint.route('/devices', methods=['GET'])
def devices_page() -> Union[str, Tuple[str, int]]:
    """
    Render the devices page for a specific plant.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_devices()
    except Exception as e:
        logging.error(f"Error in devices_page: {str(e)}")
        return render_error_404()

@api_blueprint.route('/weather', methods=['GET'])
def weather_page() -> Union[str, Tuple[str, int]]:
    """
    Render the weather page for a specific plant.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_weather()
    except Exception as e:
        logging.error(f"Error in weather_page: {str(e)}")
        return render_error_404()

@api_blueprint.route('/dashboard', methods=['GET'])
def dashboard_page() -> str:
    """
    Render the dashboard page with metrics.
    
    Returns:
        str: Rendered HTML template for the dashboard
    """
    try:
        # Use Flask's render_template directly
        return render_template('dashboard.html')
    except Exception as e:
        logging.error(f"Error in dashboard_page: {str(e)}")
        return render_error_404()

# ===== API Data Routes =====

@api_blueprint.route('/api/plants', methods=['GET'])
def api_plants() -> Tuple[Response, int]:
    """
    API endpoint to get the list of plants.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    try:
        plants = get_plants()
        # Add authentication status to the response
        if isinstance(plants, list):
            for plant in plants:
                plant['authenticated'] = True
        return jsonify(json.loads(json.dumps(plants, ensure_ascii=False))), 200
    except Exception as e:
        error_message = f"Error in api_plants: {str(e)}"
        current_app.logger.error(error_message)
        return jsonify([{
            "error": str(e), 
            "code": "API_ERROR", 
            "ui_message": "An error occurred while fetching plant data",
            "authenticated": False
        }]), 500

@api_blueprint.route('/api/devices/', methods=['GET'])
def api_get_devices() -> Tuple[Response, int]:
    """
    API endpoint to get the list of devices for all plants.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    try:
        plants = get_plants()
        plant_ids = [plant['id'] for plant in plants]
        devices = []
        
        for plant_id in plant_ids:
            plant_devices = get_devices_for_plant(plant_id)
            
            if isinstance(plant_devices, list):
                device_data = plant_devices
            else:
                device_data = plant_devices.get('datas', [])

            for device in device_data:
                status_map = {
                    '0': 'Waiting',
                    '1': 'Online',
                    None: 'Unknown'
                }
                status = status_map.get(device.get('status'), 'Offline')
                
                devices.append({
                    "alias": device.get('alias', ''),
                    "serial_number": device.get('sn', ''),
                    "plant_name": device.get('plantName', ''),
                    "total_energy": f"{device.get('eTotal', 0)} kWh",
                    "last_update_time": device.get('lastUpdateTime', ''),
                    "status": status
                })
                
        return jsonify(json.loads(json.dumps(devices, ensure_ascii=False))), 200
    except Exception as e:
        logging.error(f"Error in api_get_devices: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/api/weather', methods=['GET'])
def api_weather() -> Tuple[Response, int]:
    """
    API endpoint to get weather data for all plants.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    try:
        plants = get_plants()
        if plants and isinstance(plants, list) and len(plants) > 0 and plants[0].get('error'):
            return jsonify({"status": "error", "message": plants[0]['error']}), 401
            
        plant_ids = [plant['id'] for plant in plants]
        weather_list = []
        
        for plant_id in plant_ids:
            weather = get_weather_list(plant_id)
            if isinstance(weather, dict) and 'error' in weather:
                continue
                
            if weather:
                weather_list.append({
                    "plant_id": plant_id,
                    "weather": weather
                })
                
        return jsonify(json.loads(json.dumps(weather_list, ensure_ascii=False))), 200
    except Exception as e:
        logging.error(f"Error in api_weather: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===== Authentication Routes =====
            
@api_blueprint.route('/api/access', methods=['GET', 'POST'])
def access_api() -> Union[Response, WerkzeugResponse]:
    """ 
    Authenticate and get access to the Growatt API.
    
    Returns:
        Union[Response, WerkzeugResponse]: JSON response or redirect
    """
    try:
        result = get_access_api()
        logging.info("Access credentials retrieved successfully")
        
        if result["success"]:
            response = make_response(jsonify({
                "status": "success", 
                "message": "Authentication successful"
            }))
            
            # Set secure cookie (enable secure=True in production)
            response.set_cookie(
                'ACCESS_GROWATT', 
                json.dumps(result),
                max_age=3600,  # 1 hour expiry
                httponly=True,
                samesite='Lax'
            )
            
            if request.method == 'GET':
                return make_response(jsonify({"status": "success"}), 302, {"Location": "/plants"})
            return response
        else:
            return jsonify({"status": "error", "message": "Failed to authenticate"}), 401
            
    except Exception as e:
        logging.error(f"Access error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/api/logout', methods=['GET', 'POST'])
def logout() -> Union[Response, WerkzeugResponse]:
    """
    Logout from the Growatt client and clear all cache.
    
    Returns:
        Union[Response, WerkzeugResponse]: JSON response or redirect
    """
    try:
        # Call the logout API function
        logout_result = get_logout()
        if not logout_result['success']:
            return jsonify({"status": "error", "message": logout_result['message']}), 500
        
        # Clear Flask session data - safely handle the case where session might not be available
        try:
            session.clear()
        except RuntimeError as e:
            current_app.logger.warning(f"Session clear failed: {e}")
            # Continue with logout process even if session clear fails
        
        # Log the successful logout
        current_app.logger.info("User logged out successfully and cache cleared")
        
        response = make_response(jsonify({
            "status": "success", 
            "message": "Logout successful, all cache cleared"
        }))
        
        # Clear the session cookie
        response.delete_cookie('GROWATT_API_ACCESS')
        
        # Redirect to index page for GET requests
        if request.method == 'GET':
            return make_response('', 302, {"Location": "/"})
        return response
    except Exception as e:
        current_app.logger.error(f"Error in logout: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500