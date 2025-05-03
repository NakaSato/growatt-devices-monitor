#!/usr/bin/env python3
"""
Device Status Tracking Service

This script runs the device status tracker as a background service.
It checks for device status changes periodically and sends notifications
when devices go offline or return online.
"""
import os
import sys
import time
import logging
import argparse
import signal
from datetime import datetime

# Add the parent directory to the path to import the app module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.services.device_status_tracker import DeviceStatusTracker
from app.core import device_status
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(parent_dir, 'logs', 'device_status_service.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the Device Status Tracker service')
    parser.add_argument('--interval', type=int, default=Config.DEVICE_STATUS_CHECK_INTERVAL_MINUTES,
                        help='Check interval in minutes (default: from config)')
    parser.add_argument('--offline-threshold', type=int, default=Config.DEVICE_OFFLINE_THRESHOLD_MINUTES,
                        help='Minutes after which a device is considered offline (default: from config)')
    parser.add_argument('--cooldown', type=int, default=Config.NOTIFICATION_COOLDOWN_SECONDS,
                        help='Seconds between notifications for the same device (default: from config)')
    return parser.parse_args()


def main():
    """Main function to run the device status service."""
    args = parse_args()
    
    # Initialize the device status tracker
    tracker = DeviceStatusTracker()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Starting device status service with interval {args.interval} minutes")
    logger.info(f"Offline threshold: {args.offline_threshold} minutes")
    logger.info(f"Notification cooldown: {args.cooldown} seconds")
    
    # Main service loop
    try:
        while True:
            try:
                logger.info("Checking device statuses...")
                results = tracker.check_all_devices()
                
                # Log results
                offline_count = results.get('offline', 0)
                online_count = results.get('online', 0)
                logger.info(f"Check completed: {offline_count} offline notifications, {online_count} online notifications")
                
                # Sleep until next check
                logger.info(f"Next check in {args.interval} minutes")
                time.sleep(args.interval * 60)
                
            except Exception as e:
                logger.error(f"Error checking device statuses: {e}")
                logger.info("Retrying in 60 seconds...")
                time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in service: {e}")
    
    logger.info("Device status service stopped")


if __name__ == "__main__":
    main()