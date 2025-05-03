#!/usr/bin/env python3
"""
Send Offline Device Notifications

This script sends Telegram notifications for all currently offline Growatt devices.
It can be used manually or as part of a cron job.
"""

import os
import sys
import logging
import argparse
import time
from datetime import datetime

# Add the parent directory to the path to import the app module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.services.device_status_tracker import DeviceStatusTracker
from app.core import device_status
from app.services.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(parent_dir, 'logs', 'device_notifications.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Send Telegram notifications for offline Growatt devices')
    parser.add_argument('--force', action='store_true', help='Force notifications even if cooldown period not expired')
    parser.add_argument('--test', action='store_true', help='Send test notification instead of checking device status')
    parser.add_argument('--check-only', action='store_true', help='Only check and list offline devices, do not send notifications')
    return parser.parse_args()


def main():
    """Main function to send notifications for offline devices."""
    args = parse_args()
    
    # Initialize the device status tracker and notification service
    tracker = DeviceStatusTracker()
    notification_service = NotificationService()
    
    # If test mode is enabled, send a test notification and exit
    if args.test:
        logger.info("Sending test notifications...")
        results = tracker.test_notifications()
        
        for channel, success in results.items():
            if success:
                logger.info(f"{channel.title()} notification sent successfully")
            else:
                logger.error(f"{channel.title()} notification failed")
        
        return
    
    # Get offline devices
    logger.info("Checking for offline devices...")
    offline_devices = tracker.get_offline_devices()
    
    if not offline_devices:
        logger.info("No offline devices found.")
        return
    
    logger.info(f"Found {len(offline_devices)} offline device(s)")
    
    # List the offline devices
    for device in offline_devices:
        logger.info(f"Offline: {device.get('alias', 'Unknown')} ({device.get('serial_number')}) - Last update: {device.get('last_update_time', 'Unknown')}")
    
    # If check-only mode is enabled, exit without sending notifications
    if args.check_only:
        logger.info("Check-only mode enabled, no notifications sent")
        return
    
    # Send notifications for offline devices
    logger.info("Sending notifications for offline devices...")
    notification_count = 0
    
    for device in offline_devices:
        try:
            serial = device.get('serial_number')
            alias = device.get('alias', 'Unknown Device')
            
            # Check if force mode is enabled or if we need to respect cooldown
            should_notify = args.force
            
            if not should_notify:
                # Check if we've already notified about this device recently
                device_status = tracker.device_statuses.get(serial, {})
                last_notification_time = device_status.get('last_notification_time')
                
                if not last_notification_time or not device_status.get('notified_offline', False):
                    # Haven't notified about this device being offline yet
                    should_notify = True
            
            if should_notify:
                # Prepare notification message
                message = device_status.prepare_device_notification(device)
                
                # Send notification
                success = notification_service.send_notification(
                    message,
                    subject=f"⚠️ Device Offline: {alias} ({serial})"
                )
                
                if success:
                    logger.info(f"Sent offline notification for {alias} ({serial})")
                    notification_count += 1
                    
                    # Update the status to prevent duplicate notifications
                    if serial in tracker.device_statuses:
                        tracker.device_statuses[serial]['notified_offline'] = True
                        tracker.device_statuses[serial]['last_notification_time'] = datetime.now().isoformat()
                else:
                    logger.warning(f"Failed to send notification for {alias} ({serial})")
            else:
                logger.info(f"Skipping notification for {alias} ({serial}) - already notified recently")
                
        except Exception as e:
            logger.error(f"Error sending notification for device {device.get('serial_number')}: {e}")
    
    # Save updated device statuses if any notifications were sent
    if notification_count > 0:
        tracker._save_status_cache()
        
    logger.info(f"Sent {notification_count} notifications for offline devices")


if __name__ == "__main__":
    main()