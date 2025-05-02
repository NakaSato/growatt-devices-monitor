import logging
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from app.config import Config
from app.services.notification_service import NotificationService
from app.database import DatabaseConnector

# Configure logging
logger = logging.getLogger(__name__)

class DeviceStatusTracker:
    """Tracks device status and sends notifications when status changes"""
    
    def __init__(self):
        """Initialize the device status tracker"""
        self.notification_service = NotificationService()
        self.db = DatabaseConnector()
        self.device_statuses = {}  # Cache of last known device statuses
        self.offline_threshold_minutes = Config.DEVICE_OFFLINE_THRESHOLD_MINUTES
        
        # Load current device statuses from database on startup
        self._load_device_statuses()
        
        logger.info(f"Device status tracker initialized with {len(self.device_statuses)} devices")
    
    def _load_device_statuses(self):
        """Load current device statuses from the database"""
        try:
            devices = self.db.query(
                """
                SELECT d.serial_number, d.alias, d.status, d.last_update_time, 
                       p.id as plant_id, p.name as plant_name
                FROM devices d
                LEFT JOIN plants p ON d.plant_id = p.id
                """
            )
            
            for device in devices:
                self.device_statuses[device['serial_number']] = {
                    'serial_number': device['serial_number'],
                    'alias': device['alias'],
                    'status': device['status'],
                    'last_update_time': device['last_update_time'],
                    'plant_id': device['plant_id'],
                    'plant_name': device['plant_name'],
                    'is_offline': self._is_device_offline(device['status'], device['last_update_time']),
                    'notified_offline': False  # Track if we've already sent an offline notification
                }
            
            logger.debug(f"Loaded {len(devices)} device statuses from database")
        except Exception as e:
            logger.error(f"Error loading device statuses: {str(e)}")
    
    def _is_device_offline(self, status: str, last_update_time: Optional[str]) -> bool:
        """
        Determine if a device is considered offline based on its status and last update time
        
        Args:
            status: Current status of the device
            last_update_time: Last time the device was updated
            
        Returns:
            bool: True if the device is considered offline, False otherwise
        """
        # If status explicitly indicates offline
        if status and status.lower() in ['offline', 'disconnected', 'error']:
            return True
        
        # Check if device hasn't been updated recently
        if last_update_time:
            try:
                # Convert string timestamp to datetime
                last_update = datetime.fromisoformat(last_update_time.replace('Z', '+00:00'))
                threshold = datetime.now(last_update.tzinfo) - timedelta(minutes=self.offline_threshold_minutes)
                
                # If last update is older than threshold, consider device offline
                return last_update < threshold
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing last_update_time '{last_update_time}': {str(e)}")
        
        # Default to considering device online if we can't determine status
        return False
    
    def check_and_notify_status_changes(self, devices: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Check for device status changes and send notifications if needed
        
        Args:
            devices: List of device data dictionaries from data collection
            
        Returns:
            Dict[str, int]: Counts of notifications sent by type
        """
        if not devices:
            logger.debug("No devices provided to check for status changes")
            return {'offline': 0, 'online': 0}
        
        results = {'offline': 0, 'online': 0}
        
        for device in devices:
            serial_number = device.get('serial_number')
            if not serial_number:
                logger.warning(f"Device missing serial number: {device}")
                continue
            
            # Get current status information
            status = device.get('status', '')
            last_update_time = device.get('last_update_time')
            is_currently_offline = self._is_device_offline(status, last_update_time)
            
            # Get last known status from our tracking
            last_status = self.device_statuses.get(serial_number, {})
            was_offline = last_status.get('is_offline', False)
            notified_offline = last_status.get('notified_offline', False)
            
            # Update the cached status
            self.device_statuses[serial_number] = {
                'serial_number': serial_number,
                'alias': device.get('alias', last_status.get('alias', 'Unknown Device')),
                'status': status,
                'last_update_time': last_update_time,
                'plant_id': device.get('plant_id', last_status.get('plant_id')),
                'plant_name': device.get('plant_name', last_status.get('plant_name', 'Unknown Plant')),
                'is_offline': is_currently_offline,
                'notified_offline': notified_offline
            }
            
            # Check for status changes
            if is_currently_offline and not was_offline:
                # Device just went offline - send notification
                logger.info(f"Device {serial_number} ({device.get('alias', 'Unknown')}) has gone offline")
                
                notification_sent = self.notification_service.send_device_offline_notification(self.device_statuses[serial_number])
                if notification_sent:
                    # Update notification tracking
                    self.device_statuses[serial_number]['notified_offline'] = True
                    results['offline'] += 1
                    
            elif not is_currently_offline and was_offline and notified_offline:
                # Device was offline but is now online, and we previously sent an offline notification
                logger.info(f"Device {serial_number} ({device.get('alias', 'Unknown')}) is back online")
                
                notification_sent = self.notification_service.send_device_online_notification(self.device_statuses[serial_number])
                if notification_sent:
                    # Reset notification tracking
                    self.device_statuses[serial_number]['notified_offline'] = False
                    results['online'] += 1
        
        return results
    
    def check_all_devices(self) -> Dict[str, int]:
        """
        Check all devices in the database for status changes and send notifications if needed
        
        Returns:
            Dict[str, int]: Counts of notifications sent by type
        """
        try:
            devices = self.db.query(
                """
                SELECT d.serial_number, d.alias, d.status, d.last_update_time, 
                       p.id as plant_id, p.name as plant_name
                FROM devices d
                LEFT JOIN plants p ON d.plant_id = p.id
                """
            )
            
            return self.check_and_notify_status_changes(devices)
            
        except Exception as e:
            logger.error(f"Error checking all devices for status changes: {str(e)}")
            return {'offline': 0, 'online': 0}
    
    def get_offline_devices(self) -> List[Dict[str, Any]]:
        """
        Get a list of all currently offline devices
        
        Returns:
            List[Dict[str, Any]]: List of offline device data
        """
        offline_devices = []
        
        for serial_number, device in self.device_statuses.items():
            if device.get('is_offline', False):
                offline_devices.append(device)
        
        return offline_devices
    
    def test_notifications(self) -> Dict[str, bool]:
        """
        Test notification channels by sending test messages
        
        Returns:
            Dict[str, bool]: Test results for each notification channel
        """
        return self.notification_service.test_notification_channels()