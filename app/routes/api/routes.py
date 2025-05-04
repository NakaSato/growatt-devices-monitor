import json
import datetime
from typing import Union, Tuple, List, Dict, Any

from flask import (
    Blueprint, render_template, current_app, jsonify, 
    session, request, make_response, Response
)
from werkzeug.wrappers import Response as WerkzeugResponse

from app.services.plant_service import get_maps_plants

# Import from common helpers module
from app.routes.common.api_helpers import (
    get_plant_fault_logs, get_plants, get_devices_for_plant, get_weather_list,
    get_access_api, get_logout, get_plant_by_id, growatt_api, is_session_valid, ensure_login
)

from app.cache_utils import cached_route

# Create a blueprint for the API routes
api_blueprint = Blueprint('api_routes', __name__, url_prefix='/api')

# Helper function to log API requests
def log_api_request(endpoint):
    """
    Helper function to log API requests with consistent formatting
    
    Args:
        endpoint (str): The API endpoint being accessed
    """
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    method = request.method
    query_params = request.args.to_dict() if request.args else {}
    
    # Remove sensitive data if present in query params
    if 'password' in query_params:
        query_params['password'] = '******'
    
    # Log request details
    current_app.logger.info(
        f"API Request: {method} {endpoint} - "
        f"Client IP: {client_ip}, User-Agent: {user_agent}, "
        f"Query Params: {json.dumps(query_params)}"
    )
    
    return datetime.datetime.now()  # Return start time for response timing

# Helper function to log API responses
def log_api_response(endpoint, start_time, status_code, response_data=None, error=None):
    """
    Helper function to log API responses with consistent formatting
    
    Args:
        endpoint (str): The API endpoint being accessed
        start_time (datetime): The start time of the request
        status_code (int): The HTTP status code of the response
        response_data (any, optional): Data returned in the response
        error (Exception, optional): Exception that occurred during processing
    """
    response_time = (datetime.datetime.now() - start_time).total_seconds() * 1000  # in milliseconds
    
    if error:
        current_app.logger.error(
            f"API Error: {endpoint} - "
            f"Status: {status_code} - Error: {str(error)} - "
            f"Response time: {response_time:.2f}ms"
        )
    else:
        # For successful responses, log basic info about the response
        response_info = ""
        if isinstance(response_data, list):
            response_info = f"{len(response_data)} items returned"
        elif isinstance(response_data, dict):
            response_info = f"{len(response_data)} keys in response"
            
        current_app.logger.info(
            f"API Response: {endpoint} - "
            f"Status: {status_code} - {response_info} - "
            f"Response time: {response_time:.2f}ms"
        )

# ===== API Data Routes =====

@api_blueprint.route('/activities', methods=['GET'])
def activity_data() -> Tuple[Response, int]:
    """
    API endpoint to get recent system activities.
    
    Returns:
        Tuple[Response, int]: JSON response with activities and status code
    """
    start_time = log_api_request('/api/activities')
    
    try:
        # In a real implementation, you would fetch this from a database
        # For now, we're generating mock data
        current_time = datetime.datetime.now()
        
        activities = [
            {
                "id": 1,
                "type": "energy",
                "title": "Daily Production Record",
                "message": 'Plant "Main Residence" achieved its highest daily production of 45.7 kWh.',
                "source": "Plant: Main Residence",
                "timestamp": (current_time - datetime.timedelta(hours=1.5)).isoformat(),
                "actionText": "View Details"
            },
            {
                "id": 2,
                "type": "device",
                "title": "Inverter Reconnected",
                "message": 'Inverter "Growatt-7500" reconnected to the network after a temporary disconnection.',
                "source": "Device: Growatt-7500",
                "timestamp": (current_time - datetime.timedelta(hours=4)).isoformat(),
                "actionText": "Check Status"
            },
            {
                "id": 3,
                "type": "system",
                "title": "System Update Completed",
                "message": "Monitoring system was updated to version 2.3.4 with improved performance metrics.",
                "source": "System",
                "timestamp": (current_time - datetime.timedelta(hours=10)).isoformat(),
                "actionText": "See Changes"
            },
            {
                "id": 4,
                "type": "alert",
                "title": "Low Battery Warning Cleared",
                "message": 'The low battery warning for the "East Wing" battery system has been resolved.',
                "source": "Battery System: East Wing",
                "timestamp": (current_time - datetime.timedelta(hours=24)).isoformat(),
                "actionText": None
            }
        ]
        
        response = {"activities": activities}
        log_api_response('/api/activities', start_time, 200, response)
        return jsonify(response), 200
    except Exception as e:
        log_api_response('/api/activities', start_time, 500, error=e)
        return jsonify({
            "status": "error", 
            "message": str(e),
            "activities": []
        }), 500

@api_blueprint.route('/plants', methods=['GET'])
@cached_route(timeout=300, key_prefix='api_plants_')
def api_plants() -> Tuple[Response, int]:
    """
    API endpoint to get the list of plants.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    start_time = datetime.datetime.now()
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Log the API request
    current_app.logger.info(f"API Request: /api/plants - Client IP: {client_ip}, User-Agent: {user_agent}")
    
    try:
        plants = get_plants()
        # Add authentication status to the response
        if isinstance(plants, list):
            for plant in plants:
                plant['authenticated'] = True
                
        # Calculate response time and log the successful response
        response_time = (datetime.datetime.now() - start_time).total_seconds() * 1000  # in milliseconds
        current_app.logger.info(f"API Response: /api/plants - Success - {len(plants) if isinstance(plants, list) else 0} plants returned - Response time: {response_time:.2f}ms")
        
        return jsonify(json.loads(json.dumps(plants, ensure_ascii=False))), 200
    except Exception as e:
        error_message = f"Error in api_plants: {str(e)}"
        # Log detailed error information including client details
        response_time = (datetime.datetime.now() - start_time).total_seconds() * 1000  # in milliseconds
        current_app.logger.error(f"API Error: /api/plants - Client IP: {client_ip} - Error: {error_message} - Response time: {response_time:.2f}ms")
        
        return jsonify([{
            "error": str(e), 
            "code": "API_ERROR", 
            "ui_message": "An error occurred while fetching plant data",
            "authenticated": False
        }]), 500

@api_blueprint.route('/plants/<int:plant_id>', methods=['GET'])
def api_plant_detail(plant_id: int) -> Tuple[Response, int]:
    """
    API endpoint to get details for a specific plant.
    
    Args:
        plant_id (int): The ID of the plant to fetch
    
    Returns:
        Tuple[Response, int]: JSON response with plant data and status code
    """
    start_time = log_api_request(f'/api/plants/{plant_id}')
    
    try:
        # Get the plant detail using the get_plant_by_id helper function
        plant_data = get_plant_by_id(str(plant_id))
        
        # Check if plant exists or if we got an error
        if not plant_data:
            error_msg = f"Plant with ID {plant_id} not found"
            log_api_response(f'/api/plants/{plant_id}', start_time, 404, error=error_msg)
            return jsonify({
                "status": "error",
                "message": error_msg,
                "code": "PLANT_NOT_FOUND",
                "ui_message": "The requested plant could not be found. It may have been removed or you may not have access to it."
            }), 404
        
        # Check if we got an error response
        if isinstance(plant_data, dict) and plant_data.get('status') == 'error':
            error_code = plant_data.get('code', 'API_ERROR')
            error_message = plant_data.get('message', f"Error fetching plant ID {plant_id}")
            status_code = 401 if error_code == 'AUTH_ERROR' else 500
            
            log_api_response(f'/api/plants/{plant_id}', start_time, status_code, error=error_message)
            return jsonify(plant_data), status_code
        
        log_api_response(f'/api/plants/{plant_id}', start_time, 200, plant_data)
        return jsonify(plant_data), 200
    except Exception as e:
        log_api_response(f'/api/plants/{plant_id}', start_time, 500, error=e)
        return jsonify({
            "status": "error",
            "message": str(e),
            "code": "API_ERROR",
            "ui_message": "An error occurred while fetching plant details."
        }), 500

@api_blueprint.route('/devices', methods=['GET'])
@cached_route(timeout=300, key_prefix='api_devices_')
def api_get_devices() -> Tuple[Response, int]:
    """
    API endpoint to get the list of devices for all plants.
    Gets devices for all plants using the pagination-aware get_device_list method.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    start_time = log_api_request('/api/devices')
    
    try:
        # Get all plants
        plants = get_plants()
        
        # Log detailed information about plants
        current_app.logger.info(f"Retrieved {len(plants) if isinstance(plants, list) else 0} plants for device listing")
        
        # Check for authentication errors
        if plants and isinstance(plants, list) and len(plants) > 0 and plants[0].get('error'):
            error_msg = plants[0].get('error', 'Authentication error')
            log_api_response('/api/devices', start_time, 401, error=error_msg)
            return jsonify({"status": "error", "message": error_msg}), 401
        
        # Collect devices for all plants
        all_devices = []
        plants_with_errors = []
        successful_plants_count = 0
        retrieved_devices_count = 0
        
        if isinstance(plants, list):
            for plant in plants:
                try:
                    plant_id = plant.get('id')
                    if plant_id:
                        current_app.logger.info(f"Fetching devices for plant: {plant_id} - {plant.get('plantName', '')}")
                        
                        # Get start time for this plant's device fetch operation
                        plant_fetch_start = datetime.datetime.now()
                        
                        try:
                            # Use get_devices_for_plant which calls the pagination-aware get_device_list method
                            plant_devices = get_devices_for_plant(plant_id)
                            
                            # Log the API response structure to help with debugging
                            if current_app.config.get('DEBUG', False):
                                if isinstance(plant_devices, dict):
                                    current_app.logger.debug(f"Device response keys: {plant_devices.keys()}")
                                    # Log additional information if result and obj keys exist
                                    if 'result' in plant_devices and 'obj' in plant_devices:
                                        current_app.logger.debug(f"Response contains standard Growatt API format with result: {plant_devices['result']}")
                                        if isinstance(plant_devices['obj'], dict):
                                            obj_keys = plant_devices['obj'].keys()
                                            current_app.logger.debug(f"Obj keys: {obj_keys}")
                                            if 'totalCount' in obj_keys:
                                                current_app.logger.debug(f"Total device count: {plant_devices['obj']['totalCount']}")
                                current_app.logger.debug(f"Device response type: {type(plant_devices)}")
                            
                            # Print full response data for debugging
                            if current_app.config.get('DEBUG', False):
                                current_app.logger.debug(f"Full response data for plant {plant_id}:")
                                current_app.logger.debug(json.dumps(plant_devices, indent=2, ensure_ascii=False))
                                current_app.logger.debug("="*80)
                            
                            # Handle case where response is an empty list, integer, or other non-list/dict type
                            if isinstance(plant_devices, int) or (not isinstance(plant_devices, (list, dict))):
                                error_msg = f"Unexpected response type: {type(plant_devices).__name__}"
                                current_app.logger.error(f"Error fetching devices for plant ID {plant_id}: object of type '{type(plant_devices).__name__}' has no len()")
                                plants_with_errors.append({
                                    'plant_id': plant_id,
                                    'plant_name': plant.get('plantName', ''),
                                    'error': error_msg
                                })
                                continue
                            
                            # Handle empty list response
                            if isinstance(plant_devices, list) and len(plant_devices) == 0:
                                current_app.logger.info(f"No devices found for plant {plant_id}")
                                continue
                                
                        except Exception as fetch_error:
                            error_msg = f"API error: {str(fetch_error)}"
                            current_app.logger.error(f"Error fetching devices for plant ID {plant_id}: {error_msg}")
                            plants_with_errors.append({
                                'plant_id': plant_id,
                                'plant_name': plant.get('plantName', ''),
                                'error': error_msg
                            })
                            continue
                        
                        # Calculate fetch time for this plant
                        plant_fetch_time = (datetime.datetime.now() - plant_fetch_start).total_seconds() * 1000  # in ms
                        
                        # Handle dict response format (pagination response)
                        if isinstance(plant_devices, dict):
                            # Check for data in dict response
                            if 'obj' in plant_devices and isinstance(plant_devices['obj'], dict) and 'datas' in plant_devices['obj']:
                                data_list = plant_devices['obj']['datas']
                                if isinstance(data_list, list):
                                    devices_count = len(data_list)
                                    retrieved_devices_count += devices_count
                                    successful_plants_count += 1
                                    
                                    current_app.logger.info(
                                        f"Successfully retrieved {devices_count} devices for plant {plant_id} "
                                        f"in {plant_fetch_time:.2f}ms"
                                    )
                                    plant_devices = data_list  # Use the extracted data list for further processing
                                else:
                                    current_app.logger.warning(
                                        f"Unexpected 'datas' type in response for plant {plant_id}: {type(data_list)}"
                                    )
                                    continue
                            elif 'error' in plant_devices:
                                error_msg = plant_devices.get('error', 'Unknown error')
                                current_app.logger.warning(
                                    f"Error fetching devices for plant {plant_id}: {error_msg} "
                                    f"in {plant_fetch_time:.2f}ms"
                                )
                                plants_with_errors.append({
                                    'plant_id': plant_id,
                                    'plant_name': plant.get('plantName', ''),
                                    'error': error_msg
                                })
                                continue
                        
                        # Log the response with timing information
                        if isinstance(plant_devices, list):
                            devices_count = len(plant_devices)
                            retrieved_devices_count += devices_count
                            successful_plants_count += 1
                            
                            current_app.logger.info(
                                f"Successfully retrieved {devices_count} devices for plant {plant_id} "
                                f"in {plant_fetch_time:.2f}ms"
                            )
                        else:
                            current_app.logger.warning(
                                f"Unexpected response type for plant {plant_id} devices: {type(plant_devices)} "
                                f"in {plant_fetch_time:.2f}ms"
                            )
                            plants_with_errors.append({
                                'plant_id': plant_id,
                                'plant_name': plant.get('plantName', ''),
                                'error': f"Unexpected response type: {type(plant_devices)}"
                            })
                            continue
                        
                        # Add plant information to each device and filter out invalid devices
                        if isinstance(plant_devices, list):
                            valid_devices = []
                            for device in plant_devices:
                                if isinstance(device, dict):
                                    # Add plant context to each device
                                    device['plantId'] = plant_id
                                    device['plantName'] = plant.get('plantName', '')
                                    
                                    # Map API field names to frontend-friendly names for consistency
                                    if 'deviceSn' in device and 'serial_number' not in device:
                                        device['serial_number'] = device['deviceSn']
                                    if 'deviceName' in device and 'alias' not in device:
                                        device['alias'] = device['deviceName']
                                    if 'eTotal' in device and 'total_energy' not in device:
                                        device['total_energy'] = f"{device['eTotal']} kWh"
                                    if 'lastUpdateTime' in device and 'last_update_time' not in device:
                                        device['last_update_time'] = device['lastUpdateTime']
                                    
                                    # Check for required device fields to ensure it's a valid device
                                    if 'deviceSn' in device or 'sn' in device or 'serial_number' in device:
                                        valid_devices.append(device)
                                    else:
                                        current_app.logger.debug(f"Skipping invalid device without serial number: {device.keys() if isinstance(device, dict) else type(device)}")
                            
                            all_devices.extend(valid_devices)
                            current_app.logger.debug(f"Added {len(valid_devices)} valid devices from plant {plant_id}")
                except Exception as plant_error:
                    error_msg = str(plant_error)
                    current_app.logger.warning(f"Error fetching devices for plant {plant.get('id')}: {error_msg}")
                    plants_with_errors.append({
                        'plant_id': plant.get('id'),
                        'plant_name': plant.get('plantName', ''),
                        'error': error_msg
                    })
                    # Continue with other plants even if one fails
        
        # Log the final devices count and error statistics
        current_app.logger.info(
            f"Total devices retrieved: {len(all_devices)} from "
            f"{successful_plants_count}/{len(plants) if isinstance(plants, list) else 0} plants. "
            f"Plants with errors: {len(plants_with_errors)}"
        )
        
        # Cache the result
        cache_ttl = current_app.config.get('DEVICE_CACHE_TTL', 300)
        
        # Access cache through current_app.extensions
        cache = current_app.extensions.get('cache')
        if cache and hasattr(cache, 'set'):
            # Use cache.set() method to store the device list
            cache.set('api_devices', all_devices, timeout=cache_ttl)
            current_app.logger.debug(f"Cached {len(all_devices)} devices with TTL {cache_ttl}s")
        elif cache and isinstance(cache, dict):
            # Handle the case where cache is a dictionary-like object
            cache['api_devices'] = all_devices
            current_app.logger.debug(f"Cached {len(all_devices)} devices in dictionary cache")
        
        # Create the response with success metrics
        response = {
            "devices": all_devices,
            "meta": {
                "total_devices": len(all_devices),
                "plants_processed": len(plants) if isinstance(plants, list) else 0,
                "successful_plants": successful_plants_count,
                "plants_with_errors": len(plants_with_errors),
                "errors": plants_with_errors if plants_with_errors else None,
                "cached": cache is not None,
                "timestamp": datetime.datetime.now().isoformat()
            }
        }
        
        log_api_response('/api/devices', start_time, 200, response)
        return jsonify(all_devices), 200
    except Exception as e:
        error_message = f"Error fetching devices: {str(e)}"
        log_api_response('/api/devices', start_time, 500, error=e)
        return jsonify({
            "status": "error", 
            "message": error_message,
            "code": "API_ERROR",
            "ui_message": "An error occurred while fetching devices. Please try again later."
        }), 500

@api_blueprint.route('/weather', methods=['GET'])
def api_weather() -> Tuple[Response, int]:
    """
    API endpoint to get weather data for all plants.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    start_time = log_api_request('/api/weather')
    
    try:
        plants = get_plants()
        if plants and isinstance(plants, list) and len(plants) > 0 and plants[0].get('error'):
            error_msg = plants[0].get('error', 'Authentication error')
            log_api_response('/api/weather', start_time, 401, error=error_msg)
            return jsonify({"status": "error", "message": error_msg}), 401
            
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
                
        log_api_response('/api/weather', start_time, 200, weather_list)
        return jsonify(json.loads(json.dumps(weather_list, ensure_ascii=False))), 200
    except Exception as e:
        log_api_response('/api/weather', start_time, 500, error=e)
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/maps')
def get_plants_data():
    """API endpoint to get all plants data for the map"""
    start_time = log_api_request('/api/maps')
    
    try:
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
        
        response_data = {'plants': plants_data}
        log_api_response('/api/maps', start_time, 200, response_data)
        return jsonify(response_data)
    except Exception as e:
        log_api_response('/api/maps', start_time, 500, error=e)
        return jsonify({
            "status": "error", 
            "message": str(e),
            "code": "API_ERROR", 
            "ui_message": "An error occurred while fetching map data"
        }), 500

@api_blueprint.route('/management/data', methods=['GET'])
def api_management_data() -> Tuple[Response, int]:
    """
    API endpoint to get system management data for the management dashboard.
    
    Returns:
        Tuple[Response, int]: JSON response with management data and status code
    """
    start_time = log_api_request('/api/management/data')
    
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
        
        log_api_response('/api/management/data', start_time, 200, management_data)
        return jsonify(management_data), 200
    except Exception as e:
        log_api_response('/api/management/data', start_time, 500, error=e)
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
    start_time = log_api_request('/api/access')
    
    try:
        result = get_access_api()
        
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
            
            log_api_response('/api/access', start_time, 200, {"status": "success"})
            
            if request.method == 'GET':
                return make_response(jsonify({"status": "success"}), 302, {"Location": "/plants"})
            return response
        else:
            # Log the detailed authentication failure
            error_msg = result.get("message", "Failed to authenticate")
            log_api_response('/api/access', start_time, 401, error=error_msg)
            
            # Return 401 Unauthorized with error message when authentication fails
            return jsonify({
                "status": "error", 
                "message": error_msg,
                "authenticated": False
            }), 401
            
    except Exception as e:
        log_api_response('/api/access', start_time, 500, error=e)
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/logout', methods=['GET', 'POST'])
def logout() -> Union[Response, WerkzeugResponse]:
    """
    Logout from the Growatt client and clear all cache.
    
    Returns:
        Union[Response, WerkzeugResponse]: JSON response or redirect
    """
    start_time = log_api_request('/api/logout')
    
    try:
        # Call the logout API function
        logout_result = get_logout()
        if not logout_result['success']:
            log_api_response('/api/logout', start_time, 500, error=logout_result['message'])
            return jsonify({"status": "error", "message": logout_result['message']}), 500
        
        # Clear Flask session data - safely handle the case where session might not be available
        try:
            session.clear()
        except RuntimeError as e:
            current_app.logger.warning(f"Session clear failed: {e}")
            # Continue with logout process even if session clear fails
        
        response = make_response(jsonify({
            "status": "success", 
            "message": "Logout successful, all cache cleared"
        }))
        
        # Clear the session cookie
        response.delete_cookie('GROWATT_API_ACCESS')
        
        log_api_response('/api/logout', start_time, 200, {"status": "success"})
        
        # Redirect to index page for GET requests
        if request.method == 'GET':
            return make_response('', 302, {"Location": "/"})
        return response
    except Exception as e:
        log_api_response('/api/logout', start_time, 500, error=e)
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

@api_blueprint.route('/connection-status', methods=['GET'])
def api_connection_status() -> Tuple[Response, int]:
    """
    API endpoint to check the connection status to the Growatt API.
    
    Returns:
        Tuple[Response, int]: JSON response with connection status
    """
    try:
        # Check if growatt_api has been initialized
        if growatt_api is None:
            return jsonify({
                "status": "error",
                "message": "Growatt API has not been initialized",
                "authenticated": False,
                "initialized": False
            }), 500
        
        # Check if session is valid
        session_valid = is_session_valid()
        
        # If session is not valid, try to login
        login_result = {"success": False, "attempted": False}
        if not session_valid:
            login_result = ensure_login()
            login_result["attempted"] = True
        
        # Get API attributes
        api_attributes = {
            "has_login_method": hasattr(growatt_api, 'login'),
            "has_is_logged_in_property": hasattr(growatt_api, 'is_logged_in'),
            "is_logged_in": getattr(growatt_api, 'is_logged_in', False),
            "api_type": str(type(growatt_api))
        }
        
        return jsonify({
            "status": "success" if session_valid or login_result.get("success", False) else "error",
            "message": "Connection check completed",
            "session_valid": session_valid,
            "login_attempt": login_result,
            "api_info": api_attributes,
            "authenticated": session_valid or login_result.get("success", False),
            "initialized": True
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error checking API connection: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error checking API connection: {str(e)}",
            "authenticated": False,
            "initialized": False
        }), 500

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

@api_blueprint.route('/clear-cache', methods=['POST'])
def clear_cache() -> Tuple[Response, int]:
    """
    API endpoint to clear the application cache.
    
    Returns:
        Tuple[Response, int]: JSON response with status code
    """
    start_time = log_api_request('/api/clear-cache')
    
    try:
        # Get the cache instance
        cache_instance = current_app.extensions.get('cache')
        if not cache_instance:
            log_api_response('/api/clear-cache', start_time, 500, error="Cache extension not found")
            return jsonify({"status": "error", "message": "Cache extension not found"}), 500
        
        # Clear specific pattern if provided
        pattern = request.json.get('pattern') if request.is_json else None
        
        if pattern:
            from app.cache_utils import invalidate_cache_pattern
            # Clear cache keys matching the pattern
            num_cleared = invalidate_cache_pattern(pattern)
            message = f"Cleared {num_cleared} cache keys matching pattern '{pattern}'"
        else:
            # Clear all cache
            cache_instance.clear()
            message = "Cache cleared successfully"
        
        log_api_response('/api/clear-cache', start_time, 200, {"status": "success", "message": message})
        return jsonify({"status": "success", "message": message}), 200
    except Exception as e:
        error_msg = f"Error clearing cache: {str(e)}"
        log_api_response('/api/clear-cache', start_time, 500, error=error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@api_blueprint.route('/cache-stats', methods=['GET'])
def cache_stats() -> Tuple[Response, int]:
    """
    API endpoint to get cache statistics.
    
    Returns:
        Tuple[Response, int]: JSON response with cache statistics
    """
    start_time = log_api_request('/api/cache-stats')
    
    try:
        # Get the cache instance
        cache_instance = current_app.extensions.get('cache')
        if not cache_instance:
            log_api_response('/api/cache-stats', start_time, 500, error="Cache extension not found")
            return jsonify({"status": "error", "message": "Cache extension not found"}), 500
        
        stats = {}
        
        # If using Redis cache, get detailed statistics
        if hasattr(cache_instance, '_client') and cache_instance.config['CACHE_TYPE'] == 'RedisCache':
            redis_client = cache_instance._client
            info = redis_client.info()
            
            # Get key metrics 
            stats = {
                'cache_type': 'Redis',
                'keys': redis_client.dbsize(),
                'used_memory': info.get('used_memory_human', 'N/A'),
                'hit_rate': info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
                'peak_memory': info.get('used_memory_peak_human', 'N/A'),
                'clients_connected': info.get('connected_clients', 0),
                'pattern_data': {}
            }
            
            # Get stats for specific patterns
            key_patterns = [
                'api_plants_*',
                'api_devices*',
                'route_*'
            ]
            
            for pattern in key_patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    # Get TTLs for all keys matching the pattern
                    ttls = [redis_client.ttl(key) for key in keys]
                    avg_ttl = sum(ttl for ttl in ttls if ttl > 0) / max(len([ttl for ttl in ttls if ttl > 0]), 1)
                    
                    stats['pattern_data'][pattern] = {
                        'count': len(keys),
                        'avg_ttl_seconds': avg_ttl
                    }
        else:
            # For SimpleCache or other backends, provide limited info
            stats = {
                'cache_type': cache_instance.config['CACHE_TYPE'],
                'default_timeout': cache_instance.config['CACHE_DEFAULT_TIMEOUT'],
                'threshold': cache_instance.config.get('CACHE_THRESHOLD', 'N/A')
            }
        
        log_api_response('/api/cache-stats', start_time, 200, stats)
        return jsonify({
            'status': 'success',
            'stats': stats,
            'cache_config': {
                'CACHE_TYPE': current_app.config.get('CACHE_TYPE', 'Unknown'),
                'CACHE_DEFAULT_TIMEOUT': current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
                'DEVICE_CACHE_TTL': current_app.config.get('DEVICE_CACHE_TTL', 300),
                'PLANT_CACHE_TTL': current_app.config.get('PLANT_CACHE_TTL', 600)
            }
        }), 200
    except Exception as e:
        error_msg = f"Error getting cache stats: {str(e)}"
        log_api_response('/api/cache-stats', start_time, 500, error=error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500
