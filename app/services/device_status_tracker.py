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
    
    def load_status_cache(self):
        """Public method to load status cache (calls the internal implementation)"""
        if not hasattr(self, 'device_statuses') or not self.device_statuses:
            self._load_status_cache()
        return self.device_statuses
    
    def _serialize_datetime(self, obj):
        """Helper function to serialize datetime objects to ISO format strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Return default for other types
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _save_status_cache(self):
        """Save current device statuses to disk"""
        cache_file = os.path.join('app', 'data', 'device_status_cache.json')
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            
            # Create a deep copy of the status data to avoid modifying the original
            status_copy = {}
            for serial, status in self.device_statuses.items():
                status_copy[serial] = status.copy()
                # Convert datetime objects to ISO format strings
                if 'last_update_time' in status_copy[serial] and isinstance(status_copy[serial]['last_update_time'], datetime):
                    status_copy[serial]['last_update_time'] = status_copy[serial]['last_update_time'].isoformat()
                if 'last_notification_time' in status_copy[serial] and isinstance(status_copy[serial]['last_notification_time'], datetime):
                    status_copy[serial]['last_notification_time'] = status_copy[serial]['last_notification_time'].isoformat()
            
            # Save to file
            with open(cache_file, 'w') as f:
                json.dump(status_copy, f)
                
            logger.debug(f"Saved status cache for {len(self.device_statuses)} devices")
        except Exception as e:
            logger.error(f"Error saving device status cache: {e}")
    
    def save_status_cache(self, new_status=None):
        """Public method to save status cache"""
        if new_status is not None:
            self.device_statuses = new_status
        self._save_status_cache()
    
    def get_devices(self):
        """
        Get all devices from the database
        
        Returns:
            List[Dict[str, Any]]: List of device data
        """
        try:
            # First, check what columns are available in the devices table
            check_columns_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'devices'
            """
            
            column_results = self.db.query(check_columns_query)
            columns = [col.get('column_name') for col in column_results] if column_results else []
            
            logger.info(f"Available columns in devices table: {columns}")
            
            # Build query based on available columns
            select_columns = ['serial_number', 'plant_id', 'alias', 'status']
            
            # Add optional columns if they exist
            if 'last_update_time' in columns:
                select_columns.append('last_update_time')
            elif 'collected_at' in columns:
                select_columns.append('collected_at as last_update_time')
            else:
                # If neither time column exists, use current timestamp as fallback
                select_columns.append("CURRENT_TIMESTAMP::text as last_update_time")
            
            # Construct the final query
            columns_str = ', '.join(select_columns)
            query = f"""
                SELECT 
                    {columns_str}
                FROM devices
                ORDER BY serial_number, alias
            """
            
            logger.debug(f"Executing query: {query}")
            results = self.db.query(query)
            
            if not results:
                logger.warning("No devices found in database")
                return []
            
            # Add a placeholder for plant_name if needed by other parts of the code
            for device in results:
                if 'plant_name' not in device:
                    device['plant_name'] = device.get('alias', 'Unknown Plant')
                
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
    
    def check_and_notify_status_changes(self, devices: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Check for device status changes and send notifications if needed.
        
        Args:
            devices: List of device dictionaries with status information
            
        Returns:
            Dict with counts of notifications sent by type
        """
        if not devices:
            logger.info("No devices to check for status changes")
            return {"online": 0, "offline": 0}
            
        # Initialize counters for notification tracking
        notification_counts = {
            "online": 0,
            "offline": 0,
            "failed": 0
        }
        
        # Get current time for comparison
        current_time = datetime.now()
        
        # Load the current device status cache
        current_status = self.load_status_cache()
        new_status = {}
        
        # Check each device for status changes
        for device in devices:
            serial_number = device.get("serial_number")
            if not serial_number:
                continue
                
            # Get the alias - use serial number as fallback
            alias = device.get("alias") or serial_number
                
            # Get current status and last update time
            status = device.get("status", "unknown")
            
            # Process timestamp - allow both datetime objects and strings
            last_update_time_raw = device.get("last_update_time")
            last_update_time = None
            
            if isinstance(last_update_time_raw, datetime):
                last_update_time = last_update_time_raw
            elif isinstance(last_update_time_raw, str):
                try:
                    # Try parsing as ISO format first (most accurate)
                    try:
                        last_update_time = datetime.fromisoformat(last_update_time_raw)
                    except ValueError:
                        # If not ISO format, try other common formats
                        last_update_time = datetime.strptime(
                            last_update_time_raw, "%Y-%m-%d %H:%M:%S"
                        )
                except ValueError:
                    logger.warning(
                        f"Invalid timestamp format for device {serial_number}: {last_update_time_raw}"
                    )
                    # Use current time as fallback
                    last_update_time = current_time
            else:
                # Use current time if no timestamp provided
                last_update_time = current_time
                
            # Store the new status in our cache
            new_status[serial_number] = {
                "status": status,
                "last_update_time": last_update_time,
                "alias": alias
            }
            
            # Get previous status if available
            prev_status = current_status.get(serial_number, {})
            prev_status_value = prev_status.get("status", "unknown")
            prev_update_time = prev_status.get("last_update_time")
            
            # Check for status changes that require notification
            status_changed = status != prev_status_value
            
            # If device was previously unknown, don't trigger notification
            if prev_status_value == "unknown" and status_changed:
                logger.info(f"First status for device {alias} ({serial_number}): {status}")
                continue
                
            # For offline devices, check if they've been offline for longer than the threshold
            if status == "offline":
                # If device wasn't previously tracked or status changed to offline
                if status_changed or "notified_offline" not in prev_status:
                    # Only notify if the device has been offline for longer than the threshold
                    time_since_update = None
                    
                    if last_update_time:
                        time_since_update = current_time - last_update_time
                        
                    # Check if we should send offline notification
                    send_offline_notification = False
                    
                    # If status just changed to offline, wait for threshold
                    if status_changed and prev_status_value != "unknown":
                        if time_since_update and time_since_update > timedelta(minutes=self.offline_threshold_minutes):
                            send_offline_notification = True
                            logger.info(f"Device {alias} ({serial_number}) changed to offline and exceeds threshold")
                    # If offline status unchanged but we haven't notified yet
                    elif "notified_offline" not in prev_status and time_since_update and time_since_update > timedelta(minutes=self.offline_threshold_minutes):
                        send_offline_notification = True
                        logger.info(f"Device {alias} ({serial_number}) has gone offline")
                        
                    if send_offline_notification:
                        # Send notification
                        success = self._notify_device_offline(device)
                        if success:
                            new_status[serial_number]["notified_offline"] = True
                            notification_counts["offline"] += 1
                        else:
                            notification_counts["failed"] += 1
            
            # Check for devices coming back online
            elif status == "online" and prev_status_value == "offline" and "notified_offline" in prev_status:
                # Device has come back online after being offline
                success = self._notify_device_online(device)
                if success:
                    notification_counts["online"] += 1
                else:
                    notification_counts["failed"] += 1
                    
                # Remove the notified_offline flag
                if "notified_offline" in new_status[serial_number]:
                    del new_status[serial_number]["notified_offline"]
        
        # Save the updated status cache
        self.save_status_cache(new_status)
        
        # Log results
        logger.info(
            f"Status check completed: {notification_counts['offline']} offline and "
            f"{notification_counts['online']} online notifications sent, "
            f"{notification_counts['failed']} notifications failed"
        )
        
        return notification_counts
    
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
            message = (
                "<b>⚠️ Device Offline ⚠️</b>\n\n"
                f"<b>Device:</b> {device.get('alias', 'Unknown Device')}\n"
                f"<b>Serial Number:</b> {serial}\n"
                f"<b>Plant:</b> {device.get('plant_name', 'Unknown Plant')}\n"
                f"<b>Status:</b> Offline\n"
                f"<b>Last Seen:</b> {device.get('last_update_time', 'Unknown')}\n\n"
                "The device has not reported its status for some time and may require attention."
            )
            
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
                "<b>🟢 Device Back Online 🟢</b>\n\n"
                f"<b>Device:</b> {device.get('alias', 'Unknown Device')}\n"
                f"<b>Serial Number:</b> {serial}\n"
                f"<b>Plant:</b> {device.get('plant_name', 'Unknown Plant')}\n"
                f"<b>Status:</b> Online\n"
                f"<b>Last Seen:</b> {device.get('last_update_time', 'Unknown')}\n\n"
                "The device has successfully reconnected."
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
            "<b>🔔 This is a test notification from the Growatt Devices Monitor 🔔</b>\n\n"
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