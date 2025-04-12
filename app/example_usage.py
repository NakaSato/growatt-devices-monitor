from typing import Dict, Any
from flask import current_app
from app.utils import get_access_api


def use_growatt_api() -> Dict[str, Any]:
    """
    Example function demonstrating how to call get_access_api and use its return value
    
    Returns:
        Dict[str, Any]: Result of API operation
    """
    # Call get_access_api() to authenticate with Growatt API
    auth_result = get_access_api()
    
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
