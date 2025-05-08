"""
Core functionality for device status monitoring.

This module provides core functions for checking device status, 
determining if devices are offline, and preparing notification data.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

def is_device_offline(status: str, last_update_time: Optional[str], 
                     offline_threshold_minutes: int = 30) -> bool:
    """
    Determine if a device is considered offline based on its status and last update time
    
    Args:
        status: Current status of the device
        last_update_time: Last time the device was updated
        offline_threshold_minutes: Number of minutes after which a device is considered offline
            
    Returns:
        bool: True if the device is considered offline, False otherwise
    """
    # If status explicitly indicates offline
    if status and status.lower() in ['offline', 'disconnected', 'error']:
        return True
    
    # Check if device hasn't been updated recently
    if last_update_time:
        try:
            # Try multiple datetime string formats
            last_update = None
            
            # Handle different possible formats
            try:
                # Try ISO format (with optional Z or timezone)
                if isinstance(last_update_time, str):
                    last_update_time_clean = last_update_time.replace('Z', '+00:00')
                    last_update = datetime.fromisoformat(last_update_time_clean)
            except ValueError:
                pass
                
            # Try parsing a datetime with microseconds format
            if last_update is None and isinstance(last_update_time, str):
                try:
                    last_update = datetime.strptime(last_update_time, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    pass
            
            # Try parsing a simple datetime format
            if last_update is None and isinstance(last_update_time, str):
                try:
                    last_update = datetime.strptime(last_update_time, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
            
            # Try parsing a unix timestamp (integer)
            if last_update is None:
                try:
                    timestamp = float(last_update_time)
                    last_update = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError):
                    pass
            
            # If we couldn't parse the timestamp in any format, log and return
            if last_update is None:
                logger.warning(f"Could not parse last_update_time '{last_update_time}' in any supported format")
                return False
            
            # Use the parsed datetime to check if device is offline
            threshold = datetime.now().replace(tzinfo=last_update.tzinfo) - timedelta(minutes=offline_threshold_minutes)
            return last_update < threshold
            
        except Exception as e:
            logger.warning(f"Error parsing last_update_time '{last_update_time}': {str(e)}")
    
    # Default to considering device online if we can't determine status
    return False

def get_device_status_info(device: Dict[str, Any], 
                          offline_threshold_minutes: int = 30) -> Dict[str, Any]:
    """
    Get comprehensive status information for a device
    
    Args:
        device: Device data dictionary
        offline_threshold_minutes: Number of minutes after which a device is considered offline
        
    Returns:
        Dict[str, Any]: Device status information including offline status
    """
    serial_number = device.get('serial_number')
    status = device.get('status', '')
    last_update_time = device.get('last_update_time')
    
    return {
        'serial_number': serial_number,
        'alias': device.get('alias', 'Unknown Device'),
        'status': status,
        'last_update_time': last_update_time,
        'plant_id': device.get('plant_id'),
        'plant_name': device.get('plant_name', 'Unknown Plant'),
        'is_offline': is_device_offline(status, last_update_time, offline_threshold_minutes),
    }

def get_offline_devices(devices: List[Dict[str, Any]], 
                       offline_threshold_minutes: int = 30) -> List[Dict[str, Any]]:
    """
    Filter a list of devices to get only those that are offline
    
    Args:
        devices: List of device data dictionaries
        offline_threshold_minutes: Number of minutes after which a device is considered offline
        
    Returns:
        List[Dict[str, Any]]: List of offline device data
    """
    offline_devices = []
    
    for device in devices:
        status = device.get('status', '')
        last_update_time = device.get('last_update_time')
        
        if is_device_offline(status, last_update_time, offline_threshold_minutes):
            # Include in the offline list
            offline_devices.append(device)
    
    return offline_devices

def prepare_device_notification(device: Dict[str, Any]) -> str:
    """
    Prepare notification message for a device
    
    Args:
        device: Device data dictionary
        
    Returns:
        str: Formatted notification message
    """
    return (
        f"🔴 ALERT: Device Offline 🔴\n\n"
        f"Device: {device.get('alias', 'Unknown Device')}\n"
        f"Serial Number: {device.get('serial_number', 'Unknown')}\n"
        f"Plant: {device.get('plant_name', 'Unknown Plant')}\n"
        f"Last Seen: {device.get('last_update_time', 'Unknown')}\n\n"
        f"Please check the device status and connection."
    )

def check_status_changes(
    current_devices: List[Dict[str, Any]], 
    previous_statuses: Dict[str, Dict[str, Any]],
    offline_threshold_minutes: int = 30
) -> Dict[str, Union[Dict[str, int], Dict[str, Dict[str, Any]]]]:
    """
    Check for device status changes between current and previous states
    
    Args:
        current_devices: List of current device data dictionaries
        previous_statuses: Dictionary of previous device status information, keyed by serial number
        offline_threshold_minutes: Number of minutes after which a device is considered offline
        
    Returns:
        Dict with 'counts' of status changes and 'updated_statuses' with the latest state
    """
    if not current_devices:
        logger.debug("No devices provided to check for status changes")
        return {
            'counts': {'offline': 0, 'online': 0},
            'updated_statuses': previous_statuses
        }
    
    results = {'offline': 0, 'online': 0}
    updated_statuses = dict(previous_statuses)  # Create a copy to update
    
    status_changes = {
        'offline': [],  # Devices that went offline
        'online': []    # Devices that came back online
    }
    
    for device in current_devices:
        serial_number = device.get('serial_number')
        if not serial_number:
            logger.warning(f"Device missing serial number: {device}")
            continue
        
        # Get current status information
        status = device.get('status', '')
        last_update_time = device.get('last_update_time')
        is_currently_offline = is_device_offline(status, last_update_time, offline_threshold_minutes)
        
        # Get last known status from tracking
        last_status = previous_statuses.get(serial_number, {})
        was_offline = last_status.get('is_offline', False)
        notified_offline = last_status.get('notified_offline', False)
        
        # Update the cached status
        updated_statuses[serial_number] = {
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
            # Device just went offline - prepare for notification
            logger.info(f"Device {serial_number} ({device.get('alias', 'Unknown')}) has gone offline")
            status_changes['offline'].append(updated_statuses[serial_number])
            results['offline'] += 1
                
        elif not is_currently_offline and was_offline and notified_offline:
            # Device was offline but is now online, and we previously sent an offline notification
            logger.info(f"Device {serial_number} ({device.get('alias', 'Unknown')}) is back online")
            status_changes['online'].append(updated_statuses[serial_number])
            results['online'] += 1
    
    return {
        'counts': results,
        'updated_statuses': updated_statuses,
        'status_changes': status_changes
    }