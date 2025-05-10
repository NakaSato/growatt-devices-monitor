#!/usr/bin/env python3
"""
Script for sending device status notifications via Telegram

This script fetches current device statuses and sends notifications via Telegram
about their status and energy production.

Usage:
    python device_notification.py [--debug] [--force]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List
from datetime import datetime

# Configure logging to write to file
LOG_FILE = "logs/device_notifications.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def fetch_device_statuses() -> List[Dict[str, Any]]:
    """
    Fetch the current status of all devices
    
    Returns:
        List[Dict[str, Any]]: List of device status dictionaries
    """
    try:
        from app.core.growatt import GrowattAPI
        from app.config import Config
        
        # Initialize Growatt API
        growatt_api = GrowattAPI(
            username=Config.GROWATT_USERNAME,
            password=Config.GROWATT_PASSWORD,
            base_url=Config.GROWATT_BASE_URL
        )
        
        # Authenticate
        login_result = growatt_api.login()
        if not login_result.get('success', False):
            logger.error(f"Failed to login to Growatt API: {login_result.get('msg', 'Unknown error')}")
            return []
            
        # Fetch plants
        plants_result = growatt_api.get_plants()
        if not plants_result.get('success', False):
            logger.error(f"Failed to fetch plants: {plants_result.get('msg', 'Unknown error')}")
            return []
            
        plants = plants_result.get('data', [])
        devices = []
        
        # Fetch devices for each plant
        for plant in plants:
            plant_id = plant.get('plantId')
            plant_name = plant.get('plantName', 'Unknown Plant')
            
            devices_result = growatt_api.get_plant_devices(plant_id)
            if not devices_result.get('success', False):
                logger.warning(f"Failed to fetch devices for plant {plant_id}: {devices_result.get('msg', 'Unknown error')}")
                continue
                
            plant_devices = devices_result.get('data', [])
            
            # Add plant info to each device
            for device in plant_devices:
                device['plant_id'] = plant_id
                device['plant_name'] = plant_name
                
                # Get detailed device data
                serial_number = device.get('deviceSn')
                if serial_number:
                    detail_result = growatt_api.get_device_detail(serial_number)
                    if detail_result.get('success', False):
                        device_detail = detail_result.get('data', {})
                        device.update(device_detail)
                        
            devices.extend(plant_devices)
            
        return devices
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching device statuses: {e}")
        return []

def send_device_notifications(devices: List[Dict[str, Any]], force: bool = False) -> int:
    """
    Send notifications for device statuses
    
    Args:
        devices: List of device status dictionaries
        force: If True, ignore cooldown periods
        
    Returns:
        int: Number of notifications sent
    """
    try:
        from app.services.notification_service import NotificationService
        
        # Initialize notification service
        notification_service = NotificationService()
        
        # Check if Telegram is enabled
        if not notification_service.telegram_enabled:
            logger.error("Telegram notifications are not enabled. Please enable them in .env file.")
            return 0
            
        # Override cooldown if force is enabled
        if force:
            logger.info("Force mode enabled - ignoring notification cooldown")
            notification_service.notification_cooldown = 0
            
        notifications_sent = 0
        
        # Process each device
        for device in devices:
            # Extract required fields
            serial_number = device.get('deviceSn')
            if not serial_number:
                continue
                
            # Map Growatt API fields to notification service fields
            notification_data = {
                'serial_number': serial_number,
                'alias': device.get('deviceAilas', 'Unknown Device'),  # Note: API typo 'Ailas'
                'plant_id': device.get('plant_id'),
                'plant_name': device.get('plant_name', 'Unknown Plant'),
                'status': device.get('status', 'Unknown'),
                'last_update_time': device.get('lastUpdateTime'),
                'energy_today': device.get('eToday', 0),
                'energy_total': device.get('eTotal', 0)
            }
            
            # Determine notification type based on device status
            status = device.get('status')
            if status == '2':  # Offline status
                logger.info(f"Sending offline notification for device {serial_number}")
                success = notification_service.send_device_offline_notification(notification_data)
            else:
                logger.info(f"Sending status notification for device {serial_number}")
                success = notification_service.send_device_status_notification(notification_data)
                
            if success:
                notifications_sent += 1
                
        return notifications_sent
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error sending notifications: {e}")
        return 0

def main():
    """
    Main function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Send device status notifications via Telegram")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--force", action="store_true", 
                        help="Force sending notifications ignoring cooldown periods")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        logger.info("Starting device status notification script")
        
        # Fetch device statuses
        logger.info("Fetching device statuses...")
        devices = fetch_device_statuses()
        
        if not devices:
            logger.warning("No devices found or failed to fetch device statuses")
            return 1
            
        logger.info(f"Found {len(devices)} devices")
        
        # Send notifications
        logger.info("Sending notifications...")
        notifications_sent = send_device_notifications(devices, force=args.force)
        
        logger.info(f"Sent {notifications_sent} notifications")
        
        return 0 if notifications_sent > 0 else 1
        
    except Exception as e:
        logger.error(f"Error in device notification script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
