from typing import Dict, Any
from flask import current_app
import sys
import os

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Update the import to use the correct function names from the module
from app.core.growatt import get_api_access, get_devices_by_plant_list

def use_growatt_api() -> Dict[str, Any]:
    """
    Example function demonstrating how to call get_api_access and use its return value
    
    Returns:
        Dict[str, Any]: Result of API operation
    """
    # Call get_api_access() to authenticate with Growatt API
    auth_result = get_api_access()
    
    # Check if authentication was successful
    if isinstance(auth_result, dict) and auth_result.get('success', False):
        # Successfully authenticated
        current_app.logger.info("Authentication successful, proceeding with API operations")
        
        # You can access various fields from the result
        # For example, if there's a token or expiration time
        token = auth_result.get('token', '')
        expires_at = auth_result.get('expires_at', 0)
        
        # Now proceed with other API operations that require authentication
        return {
            "status": "success",
            "message": "API access granted",
            "auth_data": {
                "token": token,
                "expires_at": expires_at
            }
        }
    else:
        # Authentication failed, handle the error
        error_message = auth_result.get('message', 'Unknown authentication error') if isinstance(auth_result, dict) else "Authentication failed"
        error_code = auth_result.get('code', 'UNKNOWN_ERROR') if isinstance(auth_result, dict) else "UNKNOWN_ERROR"
        
        current_app.logger.error(f"Authentication failed: {error_message} (Code: {error_code})")
        
        # Return user-friendly error information
        return {
            "status": "error",
            "message": auth_result.get('ui_message', 'Unable to connect to Growatt service') if isinstance(auth_result, dict) else "Authentication failed",
            "error_code": error_code
        }
        
def use_devices_by_plant_list() -> Dict[str, Any]:
    """
    Example function demonstrating how to call get_devices_by_plant_list and use its return value
    
    Returns:
        Dict[str, Any]: Result of API operation
    """
    # First authenticate with Growatt API
    auth_result = get_api_access()
    
    # Check if authentication was successful
    if isinstance(auth_result, dict) and auth_result.get('success', False):
        # Authentication successful, now get devices by plant list
        devices_result = get_devices_by_plant_list()
        
        if isinstance(devices_result, dict) and devices_result.get('success', False):
            # Successfully retrieved devices
            current_app.logger.info("Successfully retrieved devices by plant list")
            
            # Access the devices data
            devices = devices_result.get('data', [])
            
            return {
                "status": "success",
                "message": "Devices retrieved successfully",
                "devices_count": len(devices),
                "devices": devices
            }
        else:
            # Failed to retrieve devices
            error_message = devices_result.get('message', 'Unknown error') if isinstance(devices_result, dict) else "Failed to retrieve devices"
            error_code = devices_result.get('code', 'UNKNOWN_ERROR') if isinstance(devices_result, dict) else "UNKNOWN_ERROR"
            
            current_app.logger.error(f"Failed to retrieve devices: {error_message} (Code: {error_code})")
            
            return {
                "status": "error",
                "message": devices_result.get('ui_message', 'Unable to retrieve devices') if isinstance(devices_result, dict) else "Failed to retrieve devices",
                "error_code": error_code
            }
    else:
        # Authentication failed
        return {
            "status": "error",
            "message": "Authentication required to retrieve devices",
            "error_code": "AUTH_REQUIRED"
        }