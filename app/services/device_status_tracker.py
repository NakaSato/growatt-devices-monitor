import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os

from app.config import Config
from app.services.notification_service import NotificationService
from app.database import DatabaseConnector
from app.core import device_status

# Configure logging
logger = logging.getLogger(__name__)

# Initialize a global tracker instance
_tracker = None

def get_tracker():
    """Get or create the global tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = DeviceStatusTracker()
    return _tracker

def check_devices_status():
    """
    Check all devices status and send notifications if there are changes.
    This function is designed to be called by the background scheduler.
    
    Returns:
        Dict[str, int]: Counts of notifications sent by type
    """
    tracker = get_tracker()
    return tracker.check_all_devices()


class DeviceStatusTracker:
    """
    Tracks device status changes and sends notifications when devices go offline or come back online.
    This class maintains state about which devices are offline and when notifications were sent.
    """
    
    def __init__(self):
        """Initialize the device status tracker"""
        self.db = DatabaseConnector()
        self.notification_service = NotificationService()
        self.device_statuses = {}  # Serial number -> status info
        self.offline_threshold_minutes = int(os.environ.get('DEVICE_OFFLINE_THRESHOLD_MINUTES', '30'))
        self.notification_cooldown_seconds = int(os.environ.get('NOTIFICATION_COOLDOWN_SECONDS', '3600'))
        
        # Try to load previous statuses from disk if available
        self._load_status_cache()
        
        logger.info(f"DeviceStatusTracker initialized with offline threshold of {self.offline_threshold_minutes} minutes")
    
    def _load_status_cache(self):
        """Load cached device statuses from disk if available"""
        cache_file = os.path.join('app', 'data', 'device_status_cache.json')
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    self.device_statuses = json.load(f)
                logger.info(f"Loaded status cache for {len(self.device_statuses)} devices")
            else:
                logger.info("No device status cache found, starting with empty state")
        except Exception as e:
            logger.error(f"Error loading device status cache: {e}")
            self.device_statuses = {}
    
    def _save_status_cache(self):
        """Save current device statuses to disk"""
        cache_file = os.path.join('app', 'data', 'device_status_cache.json')
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            
            with open(cache_file, 'w') as f:
                json.dump(self.device_statuses, f)
            logger.debug(f"Saved status cache for {len(self.device_statuses)} devices")
        except Exception as e:
            logger.error(f"Error saving device status cache: {e}")
    
    def get_devices(self):
        """
        Get all devices from the database
        
        Returns:
            List[Dict[str, Any]]: List of device data
        """
        try:
            query = """
                SELECT 
                    serial_number, 
                    plant_id, 
                    plant_name, 
                    alias, 
                    status, 
                    last_update_time 
                FROM devices
                ORDER BY plant_name, alias
            """
            
            results = self.db.query(query)
            if not results:
                logger.warning("No devices found in database")
                return []
                
            return results
        except Exception as e:
            logger.error(f"Error getting devices from database: {e}")
            return []
    
    def get_all_devices(self):
        """
        Get all devices from the database (alias for get_devices)
        
        Returns:
            List[Dict[str, Any]]: List of device data
        """
        return self.get_devices()
    
    def get_offline_devices(self):
        """
        Get all currently offline devices
        
        Returns:
            List[Dict[str, Any]]: List of offline device data
        """
        devices = self.get_devices()
        return device_status.get_offline_devices(
            devices, 
            offline_threshold_minutes=self.offline_threshold_minutes
        )
    
    def check_all_devices(self):
        """
        Check all devices for status changes and send notifications if needed.
        
        Returns:
            Dict[str, int]: Counts of notifications sent by type
        """
        try:
            # Get current devices from database
            devices = self.get_devices()
            if not devices:
                logger.warning("No devices found to check statuses")
                return {'offline': 0, 'online': 0}
            
            # Check for status changes
            results = device_status.check_status_changes(
                devices, 
                self.device_statuses,
                offline_threshold_minutes=self.offline_threshold_minutes
            )
            
            # Update internal status tracking
            self.device_statuses = results['updated_statuses']
            
            notifications_sent = {
                'offline': 0,
                'online': 0
            }
            
            # Process devices that went offline
            for device in results['status_changes']['offline']:
                # Send notification
                success = self._notify_device_offline(device)
                if success:
                    notifications_sent['offline'] += 1
                    
                    # Update notification status
                    serial = device['serial_number']
                    if serial in self.device_statuses:
                        self.device_statuses[serial]['notified_offline'] = True
                        self.device_statuses[serial]['last_notification_time'] = datetime.now().isoformat()
            
            # Process devices that came back online
            for device in results['status_changes']['online']:
                # Send notification
                success = self._notify_device_online(device)
                if success:
                    notifications_sent['online'] += 1
                    
                    # Update notification status
                    serial = device['serial_number']
                    if serial in self.device_statuses:
                        self.device_statuses[serial]['notified_offline'] = False
                        self.device_statuses[serial]['last_notification_time'] = datetime.now().isoformat()
            
            # Save updated status cache if changes occurred
            if notifications_sent['offline'] > 0 or notifications_sent['online'] > 0:
                self._save_status_cache()
                
            # Log results
            logger.info(
                f"Device status check completed: {len(devices)} devices checked, "
                f"{notifications_sent['offline']} offline notifications, "
                f"{notifications_sent['online']} online notifications"
            )
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Error checking device statuses: {e}")
            return {'offline': 0, 'online': 0}
    
    def _notify_device_offline(self, device):
        """
        Send notification that a device has gone offline
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Check cooldown period to avoid notification spam
            serial = device['serial_number']
            if serial in self.device_statuses:
                last_notification_time = self.device_statuses[serial].get('last_notification_time')
                if last_notification_time:
                    try:
                        last_notification = datetime.fromisoformat(last_notification_time.replace('Z', '+00:00'))
                        cooldown_threshold = datetime.now() - timedelta(seconds=self.notification_cooldown_seconds)
                        
                        # Skip notification if we're still in cooldown period
                        if last_notification > cooldown_threshold:
                            logger.info(
                                f"Skipping offline notification for {device['alias']} ({serial}) - "
                                f"in cooldown period"
                            )
                            return False
                    except (ValueError, TypeError):
                        # If we can't parse the timestamp, proceed with notification
                        pass
            
            # Prepare the notification message
            message = device_status.prepare_device_notification(device)
            
            # Send notification
            success = self.notification_service.send_notification(
                message,
                subject=f"⚠️ Device Offline: {device['alias']} ({serial})"
            )
            
            if success:
                logger.info(f"Sent offline notification for {device['alias']} ({serial})")
            else:
                logger.warning(f"Failed to send offline notification for {device['alias']} ({serial})")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending offline notification: {e}")
            return False
    
    def _notify_device_online(self, device):
        """
        Send notification that a device has come back online
        
        Args:
            device: Device data dictionary
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            serial = device['serial_number']
            
            # Prepare the notification message
            message = (
                f"🟢 Device Back Online 🟢\n\n"
                f"Device: {device.get('alias', 'Unknown Device')}\n"
                f"Serial Number: {serial}\n"
                f"Plant: {device.get('plant_name', 'Unknown Plant')}\n"
                f"Status: Online\n"
                f"Last Seen: {device.get('last_update_time', 'Unknown')}\n\n"
                f"The device has successfully reconnected."
            )
            
            # Send notification
            success = self.notification_service.send_notification(
                message,
                subject=f"✅ Device Online: {device['alias']} ({serial})"
            )
            
            if success:
                logger.info(f"Sent online notification for {device['alias']} ({serial})")
            else:
                logger.warning(f"Failed to send online notification for {device['alias']} ({serial})")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending online notification: {e}")
            return False
    
    def test_notifications(self):
        """
        Send test notifications through all available channels.
        
        Returns:
            Dict[str, bool]: Results of tests by channel
        """
        results = {}
        
        # Test message
        message = (
            "🔔 This is a test notification from the Growatt Devices Monitor 🔔\n\n"
            "If you received this message, notifications are working correctly.\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Test email
        if hasattr(self.notification_service, 'send_email'):
            try:
                email_success = self.notification_service.send_email(
                    message, 
                    subject="Test Notification - Growatt Monitor"
                )
                results['email'] = email_success
            except Exception as e:
                logger.error(f"Error testing email notification: {e}")
                results['email'] = False
        
        # Test Telegram
        if hasattr(self.notification_service, '_send_telegram'):
            try:
                telegram_success = self.notification_service._send_telegram(message)
                results['telegram'] = telegram_success
            except Exception as e:
                logger.error(f"Error testing Telegram notification: {e}")
                results['telegram'] = False
        
        return results