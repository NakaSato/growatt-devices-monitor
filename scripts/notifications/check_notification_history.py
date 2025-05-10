#!/usr/bin/env python3
"""
Script to check notification history for a device

This script retrieves and displays the notification history for a specified device,
allowing administrators to see when notifications were last sent.

Usage:
    python check_notification_history.py <serial_number> [--limit LIMIT] [--debug]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List
from datetime import datetime

# Configure logging to write to file
LOG_FILE = "logs/check_notification_history.log"
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

def format_datetime(timestamp):
    """Format datetime for display"""
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return timestamp
    
    if isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    return str(timestamp)

def check_notification_history(serial_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Check notification history for a device
    
    Args:
        serial_number: Device serial number
        limit: Maximum number of records to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of notification history records
    """
    try:
        from app.services.notification_service import NotificationService
        
        # Initialize notification service
        notification_service = NotificationService()
        
        # Check if the device exists in the database
        if not verify_device_exists(serial_number):
            logger.error(f"Device with serial number {serial_number} does not exist in the database")
            return []
        
        # Get notification history
        if hasattr(notification_service, 'get_device_notification_history'):
            history = notification_service.get_device_notification_history(serial_number, limit)
            return history
        else:
            logger.error("Notification service does not have get_device_notification_history method. "
                        "Update the notification_service.py file first.")
            return []
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error checking notification history: {e}")
        return []

def verify_device_exists(serial_number: str) -> bool:
    """
    Verify that a device exists in the database
    
    Args:
        serial_number: Device serial number
        
    Returns:
        bool: True if device exists, False otherwise
    """
    try:
        from app.database import DatabaseConnector
        
        # Initialize database connector
        db = DatabaseConnector()
        
        # Check if the device exists
        query = "SELECT serial_number FROM devices WHERE serial_number = %s"
        result = db.query(query, (serial_number,))
        
        return len(result) > 0
        
    except Exception as e:
        logger.error(f"Failed to verify device existence: {e}")
        return False

def main():
    """
    Main function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Check notification history for a device")
    parser.add_argument("serial_number", help="Serial number of the device to check")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of records to retrieve")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        logger.info(f"Checking notification history for device {args.serial_number}")
        
        # Get notification history
        history = check_notification_history(args.serial_number, args.limit)
        
        if not history:
            logger.info(f"No notification history found for device {args.serial_number}")
            return 0
        
        # Display notification history
        print(f"\nNotification History for Device: {args.serial_number}")
        print("-" * 80)
        print(f"{'Type':<10} | {'Sent At':<20} | {'Success':<7} | Message")
        print("-" * 80)
        
        for record in history:
            notification_type = record.get('notification_type', 'unknown')
            sent_at = format_datetime(record.get('sent_at', 'unknown'))
            success = "Yes" if record.get('success') else "No"
            message = record.get('message', '')
            
            # Truncate message for display
            if len(message) > 50:
                message = message[:47] + '...'
            
            print(f"{notification_type:<10} | {sent_at:<20} | {success:<7} | {message}")
        
        print("-" * 80)
        print(f"Found {len(history)} notification records")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in notification history check: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
