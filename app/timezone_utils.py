"""
Timezone Utilities for Growatt Devices Monitor
"""

import os
import logging
import pytz
from datetime import datetime

logger = logging.getLogger(__name__)

def get_timezone():
    """
    Get the application timezone from environment or config
    Returns a pytz timezone object defaulting to Asia/Bangkok if not configured
    """
    tz_name = os.environ.get('TIMEZONE', 'Asia/Bangkok')
    try:
        return pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone: {tz_name}, falling back to UTC")
        return pytz.UTC

def get_timezone_name():
    """Get the timezone name from environment"""
    return os.environ.get('TIMEZONE', 'Asia/Bangkok')

def get_now():
    """Get timezone-aware current datetime"""
    return datetime.now(get_timezone())

def isoformat_now():
    """Get ISO-formatted timezone-aware current datetime string"""
    return get_now().isoformat()

def format_datetime(dt=None, fmt='%Y-%m-%d %H:%M:%S'):
    """Format a datetime with the specified format string"""
    if dt is None:
        dt = get_now()
    return dt.strftime(fmt)

def timestamp_now():
    """Get current timestamp (seconds since epoch)"""
    return get_now().timestamp()
