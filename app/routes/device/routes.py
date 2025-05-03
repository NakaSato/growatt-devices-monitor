"""
Device Status API routes.
"""

import logging
from typing import Tuple, Dict, Any, List

from flask import Blueprint, jsonify, request, Response, current_app

from app.services.device_status_tracker import DeviceStatusTracker
from app.core import device_status

# Create a blueprint for device status routes
device_status_routes = Blueprint('device_status', __name__, url_prefix='/api/device-status')

# Initialize logging
logger = logging.getLogger(__name__)

@device_status_routes.route('/offline', methods=['GET'])
def get_offline_devices() -> Tuple[Response, int]:
    """
    Get a list of all currently offline devices.
    
    Returns:
        Tuple[Response, int]: JSON response with offline devices and HTTP status code
    """
    try:
        # Initialize the DeviceStatusTracker
        tracker = DeviceStatusTracker()
        
        # Get offline devices
        offline_devices = tracker.get_offline_devices()
        
        # Return the results
        return jsonify({
            "status": "success",
            "offline_count": len(offline_devices),
            "devices": offline_devices
        }), 200
    except Exception as e:
        logger.error(f"Error fetching offline devices: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "code": "TRACKER_ERROR",
            "ui_message": "An error occurred while fetching offline devices"
        }), 500

@device_status_routes.route('/check', methods=['POST'])
def check_device_statuses() -> Tuple[Response, int]:
    """
    Check all devices for status changes and send notifications if needed.
    
    Returns:
        Tuple[Response, int]: JSON response with results and HTTP status code
    """
    try:
        # Initialize the DeviceStatusTracker
        tracker = DeviceStatusTracker()
        
        # Check all devices
        results = tracker.check_all_devices()
        
        # Get the current offline devices
        offline_devices = tracker.get_offline_devices()
        
        # Get specific parameter to force Telegram notifications for offline devices
        force_telegram = request.args.get('force_telegram', 'false').lower() in ('true', '1', 't')
        
        # Send immediate Telegram notification for offline devices if requested
        telegram_sent_count = 0
        if force_telegram and offline_devices:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            
            # Send notifications for all offline devices
            for device in offline_devices:
                # Use core function to prepare the notification message
                message = device_status.prepare_device_notification(device)
                
                # Send notification via Telegram
                telegram_success = notification_service._send_telegram(message)
                if telegram_success:
                    telegram_sent_count += 1
                    
            logger.info(f"Sent {telegram_sent_count} immediate Telegram notifications for offline devices")
        
        # Return the results
        return jsonify({
            "status": "success",
            "notifications_sent": {
                "offline": results.get('offline', 0),
                "online": results.get('online', 0),
                "total": results.get('offline', 0) + results.get('online', 0),
                "telegram_manual": telegram_sent_count if force_telegram else 0
            },
            "offline_count": len(offline_devices),
            "force_telegram_used": force_telegram
        }), 200
    except Exception as e:
        logger.error(f"Error checking device statuses: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "code": "TRACKER_ERROR",
            "ui_message": "An error occurred while checking device statuses"
        }), 500

@device_status_routes.route('/test-notifications', methods=['POST'])
def test_device_notifications() -> Tuple[Response, int]:
    """
    Test notification channels by sending test messages.
    
    Returns:
        Tuple[Response, int]: JSON response with test results and HTTP status code
    """
    try:
        # Initialize the DeviceStatusTracker
        tracker = DeviceStatusTracker()
        
        # Test notification channels
        test_results = tracker.test_notifications()
        
        # Format the results
        formatted_results = {}
        for channel, success in test_results.items():
            formatted_results[channel] = {
                "success": success,
                "message": f"{channel.title()} notification test {'successful' if success else 'failed'}"
            }
        
        # Return the results
        return jsonify({
            "status": "success",
            "test_results": formatted_results,
            "any_successful": any(test_results.values())
        }), 200
    except Exception as e:
        logger.error(f"Error testing device status notifications: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "code": "NOTIFICATION_ERROR",
            "ui_message": "An error occurred while testing notifications"
        }), 500