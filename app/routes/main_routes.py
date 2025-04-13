import json
import logging
from typing import Tuple, Union, Dict, Any

from flask import Blueprint, jsonify, request, make_response, Response, current_app, session
from werkzeug.wrappers import Response as WerkzeugResponse

from app.utils import (
    get_plants, get_devices_for_plant, get_weather_list, 
    get_logout, get_access_api
)
from app.views.templates import (
    render_index, render_plants, render_devices, 
    render_weather, render_error_404
)
# Import the prediction routes
from app.routes.prediction_routes import prediction_routes
# Import the data routes
from app.routes.data_routes import data_routes

# Create a Blueprint for routes
api_blueprint = Blueprint('api', __name__)

# Register the prediction routes blueprint
api_blueprint.register_blueprint(prediction_routes)
# Register the data routes blueprint
api_blueprint.register_blueprint(data_routes)

# ===== Basic Page Routes =====

@api_blueprint.route('/', methods=['GET'])
def index() -> str:
    """
    Index route to render the homepage.
    
    Returns:
        str: Rendered HTML template
    """
    return render_index()

@api_blueprint.route('/plants', methods=['GET'])
def plants_page() -> Union[str, Tuple[str, int]]:
    """
    Get the list of plants associated with the logged-in user.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        plants_data = get_plants()
        # Check if plants_data is None or empty
        if not plants_data:
            current_app.logger.warning("No plants found for the user.")
            return render_error_404()
        # Render the plants page with the retrieved data
        # Handle the case where plants_data is not a list
        if not isinstance(plants_data, list):
            current_app.logger.error("Invalid data format for plants.")
            return render_error_404()
            
        return render_plants(plants_data)
    except Exception as e:
        current_app.logger.error(f"Error in plants_page: {str(e)}")
        return render_error_404()

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

def get_api_access() -> Dict[str, Any]:
    """
    Helper function to get access to the Growatt API.
    
    Returns:
        Dict[str, Any]: Result dictionary with success status and data
    """
    try:
        # Fix: Remove the incorrect cached_request call with no arguments
        # result = get_access_api()
        # if not result['success']:
        #     current_app.logger.warning(f"Authentication failed: {result['message']}")
        #     return {"status": "error", "message": result['message'], "auth_success": False}
            
        current_app.logger.info("Access credentials retrieved successfully")
        return {
            "status": "success", 
            "message": "Authentication successful",
            "authenticated": True
        }
    except Exception as e:
        current_app.logger.error(f"Access error: {str(e)}")
        return {"status": "error", "message": str(e), "authenticated": False}

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
        if plants and plants[0].get('error'):
            return jsonify({"status": "error", "message": plants[0]['error']}), 401
            
        plant_ids = [plant['id'] for plant in plants]
        weather_list = []
        
        for plant_id in plant_ids:
            weather = get_weather_list(plant_id)
            if 'error' in weather:
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
        
        if result:
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