#!/usr/bin/env python3
"""
Script for sending offline device status notifications via Telegram

This script specifically checks for devices with status = -1 in the database
and sends notifications via Telegram about these offline devices.

Usage:
    python offline_devices_notification.py [--debug] [--force] [--clear-history]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List
from datetime import datetime

# Configure logging to write to file
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
LOG_FILE = os.path.join(project_root, "logs", "offline_devices_notification.log")
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
# Add the project root directory to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

def fetch_offline_devices() -> List[Dict[str, Any]]:
    """
    Fetch devices with status = -1 from the database
    
    Returns:
        List[Dict[str, Any]]: List of offline device dictionaries
    """
    try:
        from app.database import DatabaseConnector
        
        # Initialize database connector
        db = DatabaseConnector()
        
        # Query for devices with status = -1
        query = """
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
                d.status = '-1'
        """
        
        # Execute the query using the DatabaseConnector
        offline_devices = db.query(query)
        
        if offline_devices:
            logger.info(f"Found {len(offline_devices)} devices with offline status (-1)")
        else:
            logger.info("No devices with offline status (-1) found")
            
        return offline_devices or []
        
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
        devices: List of offline device dictionaries
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
            logger.error("Telegram notifications are not enabled. Please check .env configuration.")
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

def clear_notification_history() -> bool:
    """
    Clear all offline notification history
    
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
        
        # Clear history for offline notifications
        query = "DELETE FROM notification_history WHERE notification_type = 'offline'"
        logger.info("Clearing offline notification history")
        
        # Execute the query
        db.execute(query)
        
        logger.info("Offline notification history cleared successfully")
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
    parser = argparse.ArgumentParser(description="Send offline device status notifications via Telegram")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--force", action="store_true", 
                        help="Force sending notifications ignoring cooldown periods")
    parser.add_argument("--clear-history", action="store_true",
                        help="Clear offline notification history before sending new notifications")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        # If clear history is requested
        if args.clear_history:
            logger.info("Clearing offline notification history requested")
            success = clear_notification_history()
            if not success:
                logger.error("Failed to clear offline notification history")
                return 1
            
            logger.info("Successfully cleared offline notification history")
                
        logger.info("Starting offline device notification script")
        
        # Fetch offline devices from database
        logger.info("Fetching devices with status = -1 from database...")
        offline_devices = fetch_offline_devices()
        
        if not offline_devices:
            logger.info("No offline devices found in the database")
            return 0
            
        logger.info(f"Found {len(offline_devices)} offline devices")
        
        # Display header information about offline devices
        print(f"\nOffline Devices (status = -1) Found: {len(offline_devices)}")
        print("-" * 80)
        print(f"{'Serial Number':<20} | {'Alias':<30} | {'Last Update':<20} | {'Plant'}")
        print("-" * 80)
        
        for device in offline_devices:
            serial = device.get('serial_number', 'Unknown')
            alias = device.get('alias', 'Unknown')
            last_update = device.get('last_update_time', 'Unknown')
            plant = device.get('plant_name', 'Unknown')
            
            if isinstance(last_update, datetime):
                last_update = last_update.strftime('%Y-%m-%d %H:%M:%S')
                
            print(f"{serial:<20} | {alias[:30]:<30} | {str(last_update)[:20]:<20} | {plant}")
        
        print("-" * 80)
        
        # Send notifications for offline devices
        logger.info("Sending notifications for offline devices...")
        notifications_sent = send_offline_device_notifications(offline_devices, force=args.force)
        
        logger.info(f"Sent {notifications_sent} notifications")
        
        return 0 if notifications_sent > 0 else 1
        
    except Exception as e:
        logger.error(f"Error in offline device notification script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
