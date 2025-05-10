#!/usr/bin/env python3
"""
Script for sending device status notifications via Telegram

This script fetches offline devices directly from the database (status = -1) 
and sends notifications via Telegram about their status.

Usage:
    python device_notification.py [--debug] [--force] [--clear-history] [--device DEVICE_SN]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List
from datetime import datetime, timedelta

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

def fetch_offline_devices_from_db() -> List[Dict[str, Any]]:
    """
    Fetch offline devices directly from the database (status = -1)
    
    Returns:
        List[Dict[str, Any]]: List of offline device status dictionaries
    """
    try:
        from app.database import DatabaseConnector
        from app.core.device_status import get_timezone, is_device_offline
        
        offline_devices = []
        offline_threshold_minutes = int(os.environ.get('DEVICE_OFFLINE_THRESHOLD_MINUTES', '30'))
        
        logger.info(f"Fetching offline devices (with status = -1 or offline for {offline_threshold_minutes} minutes)")
        
        # Initialize database connector
        db = DatabaseConnector()
        
        # Query for explicitly offline devices
        offline_query = """
            SELECT 
                d.serial_number, 
                d.alias, 
                d.plant_id, 
                d.status, 
                d.last_update_time,
                d.type,
                p.name as plant_name
            FROM 
                devices d
            LEFT JOIN 
                plants p ON d.plant_id = p.id
            WHERE 
                d.status = '-1' OR 
                LOWER(d.status) = 'offline'
        """
        
        # Execute the query using the DatabaseConnector
        explicit_offline_devices = db.query(offline_query)
        
        if explicit_offline_devices:
            logger.info(f"Found {len(explicit_offline_devices)} devices explicitly marked as offline")
            offline_devices.extend(explicit_offline_devices)
            
        # Get current time and threshold for time-based offline detection
        current_time = datetime.now(get_timezone())
        threshold_time = current_time - timedelta(minutes=offline_threshold_minutes)
        
        # Format the threshold time for SQL
        threshold_time_str = threshold_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Query for devices that haven't updated in the threshold period
        time_based_query = """
            SELECT 
                d.serial_number, 
                d.alias, 
                d.plant_id, 
                d.status, 
                d.last_update_time,
                d.type,
                p.name as plant_name
            FROM 
                devices d
            LEFT JOIN 
                plants p ON d.plant_id = p.id
            WHERE 
                d.last_update_time < %s
                AND LOWER(d.status) != 'offline'
                AND d.status != '-1'
        """
        
        # Execute query with parameter
        time_based_offline_devices = db.query(time_based_query, (threshold_time_str,))
        
        if time_based_offline_devices:
            logger.info(f"Found {len(time_based_offline_devices)} devices inactive for more than {offline_threshold_minutes} minutes")
            
            # Mark these devices as offline for notification purposes
            for device in time_based_offline_devices:
                device['status'] = 'offline'
                offline_devices.append(device)
        
        logger.info(f"Found total of {len(offline_devices)} offline devices in database")
        return offline_devices
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching offline devices from database: {e}")
        return []

def send_offline_device_notifications(devices: List[Dict[str, Any]], force: bool = False) -> int:
    """
    Send notifications for offline devices
    
    Args:
        devices: List of offline device status dictionaries
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
        
        # Process each offline device
        for device in devices:
            # Extract required fields
            serial_number = device.get('serial_number')
            if not serial_number:
                logger.warning("Skipping device with missing serial number")
                continue
                
            # Send offline notification
            logger.info(f"Sending offline notification for device {serial_number} ({device.get('alias', 'Unknown')})")
            success = notification_service.send_device_offline_notification(device)
                
            if success:
                notifications_sent += 1
                logger.info(f"Successfully sent offline notification for {serial_number}")
            else:
                logger.warning(f"Failed to send offline notification for {serial_number}")
                
        return notifications_sent
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error sending notifications: {e}")
        return 0

def clear_notification_history(device_serial: str = None) -> bool:
    """
    Clear notification history for a device or all devices
    
    Args:
        device_serial: Optional device serial number. If None, clear all history.
        
    Returns:
        bool: True if history was cleared successfully, False otherwise
    """
    try:
        from app.database import DatabaseConnector
        
        # Initialize database connector
        db = DatabaseConnector()
        
        # Check if notification_history table exists
        table_exists_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'notification_history'
            )
        """
        
        result = db.query(table_exists_query)
        
        if not result or not result[0]['exists']:
            logger.error("Notification history table does not exist in database")
            return False
        
        # Prepare query based on whether a device serial was provided
        if device_serial:
            # Clear history for specific device
            query = "DELETE FROM notification_history WHERE device_serial_number = %s"
            params = (device_serial,)
            logger.info(f"Clearing notification history for device {device_serial}")
        else:
            # Clear all history
            query = "DELETE FROM notification_history"
            params = None
            logger.info("Clearing all notification history")
        
        # Execute the query
        db.execute(query, params)
        
        logger.info("Notification history cleared successfully")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error clearing notification history: {e}")
        return False

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
    parser.add_argument("--clear-history", action="store_true",
                        help="Clear notification history before sending new notifications")
    parser.add_argument("--device", type=str, 
                        help="Specific device serial number to focus on (for sending or clearing history)")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        # If clear history is requested
        if args.clear_history:
            logger.info("Clearing notification history requested")
            success = clear_notification_history(args.device)
            if not success:
                logger.error("Failed to clear notification history")
                return 1
            
            if args.device:
                logger.info(f"Successfully cleared notification history for device {args.device}")
            else:
                logger.info("Successfully cleared all notification history")
                
            # If only clearing history was requested, exit
            if args.device and not args.force:
                return 0
                
        logger.info("Starting device notification script for offline devices")
        
        # Fetch offline devices from database
        logger.info("Fetching offline devices from database...")
        offline_devices = fetch_offline_devices_from_db()
        
        # If specific device is specified, filter the list
        if args.device and not args.clear_history:
            offline_devices = [d for d in offline_devices if d.get('serial_number') == args.device]
            if not offline_devices:
                logger.warning(f"Device {args.device} is not offline or does not exist")
                return 0
        
        if not offline_devices:
            logger.info("No offline devices found in the database")
            return 0
            
        logger.info(f"Found {len(offline_devices)} offline devices")
        
        # Send notifications for offline devices
        logger.info("Sending notifications for offline devices...")
        notifications_sent = send_offline_device_notifications(offline_devices, force=args.force)
        
        logger.info(f"Sent {notifications_sent} notifications")
        
        return 0 if notifications_sent > 0 else 1
        
    except Exception as e:
        logger.error(f"Error in device notification script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
