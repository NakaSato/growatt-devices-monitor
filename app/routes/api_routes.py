import json
import logging
from typing import Union, Tuple, List, Dict, Any

from flask import (
    Blueprint, render_template, current_app, jsonify, 
    session, request, make_response, Response
)
from werkzeug.wrappers import Response as WerkzeugResponse

from app.services.plant_service import get_maps_plants

from .api_helpers import (
    get_plant_fault_logs, get_plants, get_devices_for_plant, get_weather_list,
    get_access_api, get_logout
)

# Create a blueprint for the API routes
api_blueprint = Blueprint('api_routes', __name__, url_prefix='/api')

# ===== API Data Routes =====

@api_blueprint.route('/plants', methods=['GET'])
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

@api_blueprint.route('/devices', methods=['GET'])
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

@api_blueprint.route('/weather', methods=['GET'])
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

@api_blueprint.route('/maps')
def get_plants_data():
    """API endpoint to get all plants data for the map"""
    plants = get_maps_plants()
    
    # Format data for the map
    plants_data = [{
        'id': plant.id,
        'name': plant.name,
        'status': plant.status,
        'latitude': plant.latitude,
        'longitude': plant.longitude,
        'capacity': plant.capacity,
        'currentOutput': plant.current_output,
        'todayEnergy': plant.today_energy,
        'peakOutput': plant.peak_output,
        'installDate': plant.install_date.strftime('%Y-%m-%d') if plant.install_date else 'N/A',
        'location': plant.location
    } for plant in plants]
    
    return jsonify({
        'plants': plants_data
    })

@api_blueprint.route('/management/data', methods=['GET'])
def api_management_data() -> Tuple[Response, int]:
    """
    API endpoint to get system management data for the management dashboard.
    
    Returns:
        Tuple[Response, int]: JSON response with management data and status code
    """
    try:
        # Create a response with static management data since we're removing plant data fetching
        management_data = {
            'overview': {
                'total_plants': 0,
                'total_devices': 0,
                'total_capacity': 0,
                'devices_by_status': {
                    'online': 0,
                    'offline': 0,
                    'maintenance': 0
                },
                'plants_by_status': {
                    'active': 0,
                    'inactive': 0,
                },
                'system_uptime': 99.2,  # Static placeholder value
                'last_update': None
            },
            'plants': [],
            'devices': [],
            'health': {
                'cpu_usage': 23.5,  # Static placeholder values
                'memory_usage': 42.8,
                'disk_usage': 38.6,
                'api_status': 'operational',
                'database_status': 'operational',
                'data_collector_status': 'operational',
                'last_backup': '2023-05-02 14:30:00'
            },
            'analytics': {
                'daily_production': [
                    {'date': '2023-04-27', 'value': 203.5},
                    {'date': '2023-04-28', 'value': 198.2},
                    {'date': '2023-04-29', 'value': 210.7},
                    {'date': '2023-04-30', 'value': 205.3},
                    {'date': '2023-05-01', 'value': 215.8},
                    {'date': '2023-05-02', 'value': 207.4},
                    {'date': '2023-05-03', 'value': 212.1}
                ],
                'monthly_production': [
                    {'month': 'Jan', 'value': 5120},
                    {'month': 'Feb', 'value': 5580},
                    {'month': 'Mar', 'value': 6210},
                    {'month': 'Apr', 'value': 6350},
                    {'month': 'May', 'value': 3120}
                ]
            },
            'settings': {
                'data_collection_interval': 300,  # 5 minutes in seconds
                'notification_channels': {
                    'email': True,
                    'telegram': True,
                    'sms': False
                },
                'alert_thresholds': {
                    'production_drop': 20,  # percentage
                    'device_offline': 30  # minutes
                }
            }
        }
        
        return jsonify(management_data), 200
    except Exception as e:
        logging.error(f"Error in api_management_data: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "code": "API_ERROR",
            "ui_message": "An error occurred while fetching management data"
        }), 500

# ===== Authentication Routes =====
@api_blueprint.route('/access', methods=['GET', 'POST', 'HEAD'])
def access_api() -> Union[Response, WerkzeugResponse]:
    """ 
    Authenticate and get access to the Growatt API.
    
    Returns:
        Union[Response, WerkzeugResponse]: JSON response or redirect
    """
    try:
        result = get_access_api()
        logging.info("Access credentials retrieved successfully")
        
        if result.get("success", False):
            # Create success response
            response = make_response(jsonify({
                "status": "success", 
                "message": "Authentication successful"
            }))
            
            # Use consistent cookie name: GROWATT_API_ACCESS
            response.set_cookie(
                'GROWATT_API_ACCESS', 
                json.dumps(result),
                max_age=3600,  # 1 hour expiry
                httponly=True,
                samesite='Lax'
            )
            
            if request.method == 'GET':
                return make_response(jsonify({"status": "success"}), 302, {"Location": "/plants"})
            return response
        else:
            # Log the detailed authentication failure
            error_msg = result.get("message", "Failed to authenticate")
            logging.warning(f"Authentication failed: {error_msg}")
            
            # Return 401 Unauthorized with error message when authentication fails
            return jsonify({
                "status": "error", 
                "message": error_msg,
                "authenticated": False
            }), 401
            
    except Exception as e:
        logging.error(f"Access error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/logout', methods=['GET', 'POST'])
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

@api_blueprint.route('/debug-env', methods=['GET'])
def debug_env():
    """
    Debug endpoint to check if environment variables are loaded.
    Only enabled in development mode for security.
    """
    if current_app.config.get('DEBUG', False):
        username = current_app.config.get('GROWATT_USERNAME', 'NOT SET')
        # Mask password for security
        password = 'SET' if current_app.config.get('GROWATT_PASSWORD') else 'NOT SET'
        
        return jsonify({
            'GROWATT_USERNAME': username,
            'GROWATT_PASSWORD_SET': password,
            'DEBUG': current_app.config.get('DEBUG', False),
        })
    else:
        return jsonify({"error": "Debug endpoint only available in development mode"}), 403

# Helper rendering functions
def render_plants(plants_data: List[Dict[str, Any]]) -> str:
    """Render the plants page with data"""
    return render_template('plants.html', plants=plants_data)

def render_devices() -> str:
    """Render the devices page"""
    return render_template('devices.html')

def render_weather() -> str:
    """Render the weather page"""
    return render_template('weather.html')

def render_error_404() -> Tuple[str, int]:
    """Render a 404 error page"""
    return render_template('404.html'), 404

@api_blueprint.route('/device/fault-logs', methods=['GET', 'POST'])
def api_device_fault_logs() -> Tuple[Response, int]:
    """
    API endpoint to get fault logs for a specific device.
    
    Query Parameters:
        device_sn/deviceSn: The serial number of the device to fetch fault logs for
        plant_id/plantId: The ID of the plant to fetch fault logs for
        date: The date to fetch logs for (format: YYYY-MM-DD)
        page_num/toPageNum: Page number for pagination (default: 1)
        device_flag/deviceFlag: Flag indicating device type (0=all, 1=inverter, etc.)
        type: Type of fault log to retrieve (1=fault, 2=alarm, etc.)
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    try:
        # Support both naming conventions in parameters
        device_sn = request.args.get('device_sn') or request.args.get('deviceSn', '')
        plant_id = request.args.get('plant_id') or request.args.get('plantId')
        date = request.args.get('date')
        
        # Ensure numeric parameters are properly converted to integers
        try:
            page_num = int(request.args.get('page_num') or request.args.get('toPageNum', 1))
        except (ValueError, TypeError):
            page_num = 1
            
        try:
            device_flag = int(request.args.get('device_flag') or request.args.get('deviceFlag', 0))
        except (ValueError, TypeError):
            device_flag = 0
            
        try:
            fault_type = int(request.args.get('type', 1))
        except (ValueError, TypeError):
            fault_type = 1
        
        if not plant_id:
            return jsonify({
                "error": "Missing required parameter: plant_id/plantId",
                "code": "INVALID_PARAMETER",
                "ui_message": "Plant ID must be provided"
            }), 400
            
        current_app.logger.debug(f"Fetching fault logs for plant: {plant_id}, device: {device_sn}, date: {date}, page: {page_num}, type: {fault_type}, deviceFlag: {device_flag}")
        
        # Get fault logs with explicit parameters to avoid keyword/slicing errors
        # This ensures all parameters are properly passed by keyword
        fault_logs = get_plant_fault_logs(
            plant_id=str(plant_id), 
            date=date if date else None,
            device_sn=str(device_sn) if device_sn else "",
            page_num=page_num,
            device_flag=device_flag,
            fault_type=fault_type
        )
        
        # Check if there was an error
        if isinstance(fault_logs, dict) and 'error' in fault_logs:
            return jsonify(fault_logs), 500
        
        if isinstance(fault_logs, list) and len(fault_logs) > 0 and isinstance(fault_logs[0], dict) and 'error' in fault_logs[0]:
            return jsonify(fault_logs[0]), 500
        
        # Calculate pagination info if not already included in the response
        total_count = len(fault_logs) if isinstance(fault_logs, list) else 0
        
        response = {
            "total_count": total_count,
            "current_page": page_num,
            "device_sn": device_sn,
            "plant_id": plant_id,
            "fault_logs": fault_logs
        }
        
        return jsonify(response), 200
    except ValueError as e:
        error_message = f"Invalid parameter: {str(e)}"
        current_app.logger.error(error_message)
        return jsonify({
            "status": "error", 
            "message": str(e),
            "code": "INVALID_PARAMETER",
            "ui_message": "Invalid parameters provided"
        }), 400
    except Exception as e:
        error_message = f"Error in api_device_fault_logs: {str(e)}"
        current_app.logger.error(error_message)
        return jsonify({
            "status": "error", 
            "message": str(e),
            "code": "API_ERROR",
            "ui_message": "An error occurred while fetching fault logs"
        }), 500

@api_blueprint.route('/notifications/test', methods=['POST'])
def test_notifications() -> Tuple[Response, int]:
    """
    API endpoint to test notification channels.
    
    Returns:
        Tuple[Response, int]: JSON response with status code and test results
    """
    try:
        # Initialize device status tracker to access notification service
        from app.services.device_status_tracker import DeviceStatusTracker
        device_tracker = DeviceStatusTracker()
        
        # Test all configured notification channels
        test_results = device_tracker.test_notifications()
        
        # Format the response
        response = {
            "status": "success",
            "message": "Notification test completed",
            "results": {
                "email": {
                    "success": test_results.get("email", False),
                    "message": "Email notification test successful" if test_results.get("email", False) 
                              else "Email notification test failed or not configured"
                },
                "telegram": {
                    "success": test_results.get("telegram", False),
                    "message": "Telegram notification test successful" if test_results.get("telegram", False)
                              else "Telegram notification test failed or not configured"
                }
            },
            "any_success": any(test_results.values())
        }
        
        current_app.logger.info(f"Notification test results: {test_results}")
        return jsonify(response), 200
    except Exception as e:
        error_message = f"Error testing notifications: {str(e)}"
        current_app.logger.error(error_message)
        return jsonify({
            "status": "error", 
            "message": str(e),
            "code": "NOTIFICATION_TEST_ERROR",
            "ui_message": "An error occurred while testing notifications"
        }), 500
