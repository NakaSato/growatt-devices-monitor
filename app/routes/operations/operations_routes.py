"""
Routes for system operations and configuration management
"""

import os
import logging
from typing import Dict, Any, Tuple

from flask import Blueprint, jsonify, request, current_app

from app.config import Config

# Create a Blueprint for operations routes
operations_routes = Blueprint('operations', __name__, url_prefix='/api/operations')

@operations_routes.route('/data', methods=['GET'])
def get_operations_data() -> Tuple[Dict[str, Any], int]:
    """
    API endpoint to get system operations data.
    Returns system configuration and operational status information.
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with operations data and status code
    """
    try:
        # Get application configuration settings from Config class
        # Excluding sensitive information like passwords
        config_data = {
            "general": {
                "systemName": current_app.config.get("SYSTEM_NAME", "Growatt Monitoring System"),
                "defaultView": current_app.config.get("DEFAULT_VIEW", "dashboard"),
                "timezone": current_app.config.get("TIMEZONE", "UTC"),
                "refreshRate": current_app.config.get("REFRESH_RATE", 60),
            },
            "api": {
                "baseUrl": Config.GROWATT_BASE_URL,
                "timeout": Config.get_int("API_TIMEOUT", 10),
                "rateLimit": Config.get_int("API_RATE_LIMIT", 60),
                "cacheDuration": Config.CACHE_DEFAULT_TIMEOUT // 60,  # Convert seconds to minutes
            },
            "notifications": {
                "enableEmail": Config.EMAIL_NOTIFICATIONS_ENABLED,
                "emailAddress": Config.EMAIL_TO[0] if Config.EMAIL_TO else "",
                "emailFrequency": Config.get_str("EMAIL_FREQUENCY", "daily"),
                "enablePush": Config.TELEGRAM_NOTIFICATIONS_ENABLED,
                "notifyAlerts": Config.get_bool("NOTIFY_ALERTS", True),
                "notifyPerformance": Config.get_bool("NOTIFY_PERFORMANCE", False),
                "notifyMaintenance": Config.get_bool("NOTIFY_MAINTENANCE", True),
            },
            "advanced": {
                "debugMode": Config.DEBUG,
                "dbType": "sqlite",  # Default - can be changed based on Config
                "dbConnection": "",  # Don't expose connection strings
                "dataRetention": Config.get_int("DATA_RETENTION_DAYS", 90),
                "enableML": Config.get_bool("ENABLE_ML_FEATURES", True),
            }
        }
        
        # Set database type based on configuration
        if Config.DATABASE_URL.startswith("postgresql"):
            config_data["advanced"]["dbType"] = "postgres"
        elif Config.DATABASE_URL.startswith("mysql"):
            config_data["advanced"]["dbType"] = "mysql"
        
        # Return success response with configuration data
        return jsonify({
            "status": "success",
            "message": "Configuration data retrieved successfully",
            "config": config_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving operations data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve operations data: {str(e)}"
        }), 500


@operations_routes.route('/configuration', methods=['GET', 'POST'])
def system_configuration() -> Tuple[Dict[str, Any], int]:
    """
    API endpoint to get or update system configuration.
    GET: Returns current system configuration
    POST: Updates system configuration with provided data
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with configuration and status code
    """
    if request.method == 'GET':
        # Use the same implementation as get_operations_data
        return get_operations_data()
    
    elif request.method == 'POST':
        try:
            # Get configuration data from request
            config_data = request.get_json()
            if not config_data:
                return jsonify({
                    "status": "error",
                    "message": "No configuration data provided"
                }), 400
                
            # TODO: In a real implementation, you would save these settings
            # to a configuration database or file. For now, we'll just log
            # that we received them and return success.
            
            current_app.logger.info(f"Received configuration update: {config_data}")
            
            # Return success response
            return jsonify({
                "status": "success",
                "message": "Configuration updated successfully",
                "config": config_data
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error updating configuration: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Failed to update configuration: {str(e)}"
            }), 500