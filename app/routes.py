import json
import logging
from typing import Tuple, Dict, Any, List, Union

from flask import Blueprint, jsonify, request, make_response, Response
from werkzeug.wrappers import Response as WerkzeugResponse

from app.utils import (
    get_plants, get_devices_for_plant, get_weather_list, 
    get_logout, get_access
)
from app.views.templates import (
    render_index, render_plants, render_devices, 
    render_weather, render_error_404
)

# Create a Blueprint for routes
api_blueprint = Blueprint('api', __name__)

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
        plants = get_plants()
        return render_plants(plants)
    except Exception as e:
        logging.error(f"Error in plants_page: {str(e)}")
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

@api_blueprint.route('/api/plants', methods=['GET'])
def api_plants() -> Tuple[Response, int]:
    """
    API endpoint to get the list of plants.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    try:
        plants = get_plants()
        return jsonify(json.loads(json.dumps(plants, ensure_ascii=False))), 200
    except Exception as e:
        logging.error(f"Error in api_plants: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
        plant_ids = [plant['id'] for plant in plants]
        weather_list = []
        
        for plant_id in plant_ids:
            weather = get_weather_list(plant_id)
            if weather:
                weather_list.append({
                    "plant_id": plant_id,
                    "weather": weather
                })
                
        return jsonify(json.loads(json.dumps(weather_list, ensure_ascii=False))), 200
    except Exception as e:
        logging.error(f"Error in api_weather: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/logout', methods=['GET'])
def logout() -> str:
    """
    Logout from the Growatt client.
    
    Returns:
        str: Rendered HTML template with logout message
    """
    try:
        get_logout()
        logging.info("User logged out successfully")
        return render_index()
    except Exception as e:
        logging.error(f"Error in logout: {str(e)}")
        return render_index()

@api_blueprint.route('/api/access', methods=['GET', 'POST'])
def access_api() -> Union[Response, WerkzeugResponse]:
    """
    Authenticate and get access to the Growatt API.
    
    Returns:
        Union[Response, WerkzeugResponse]: JSON response or redirect
    """
    try:
        result = get_access()
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
