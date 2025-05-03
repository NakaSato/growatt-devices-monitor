import os
import secrets
from typing import Dict, Any, Optional, Union, cast
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env files
# Try to load from different potential locations
env_paths = [
    Path('.env'),                   # Root directory .env
    Path('.env.local'),             # Local overrides
    Path('app/.env'),               # App directory .env
    Path(os.path.expanduser('~/.env.growatt'))  # User-specific .env
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))
        print(f"Loaded environment from {env_path}")

class Config:
    """Application configuration settings
    
    All configuration is loaded from environment variables with sensible defaults.
    Set these values in a .env file for local development or through environment
    variables in production.
    """
    
    # Generate a random secret key if not provided in environment
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(16))
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Session configuration
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'False').lower() in ('true', '1', 't')
    SESSION_USE_SIGNER = os.getenv('SESSION_USE_SIGNER', 'True').lower() in ('true', '1', 't')
    PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600'))
    
    # Database configuration - PostgreSQL
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'growatt')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'growattpassword')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'growattdb')
    
    # Growatt API credentials
    GROWATT_USERNAME = os.getenv('GROWATT_USERNAME', '')
    GROWATT_PASSWORD = os.getenv('GROWATT_PASSWORD', '')
    GROWATT_BASE_URL = os.getenv('GROWATT_BASE_URL', 'https://server.growatt.com')
    
    # Notification settings
    # Email notification settings
    EMAIL_NOTIFICATIONS_ENABLED = os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'False').lower() in ('true', '1', 't')
    EMAIL_FROM = os.getenv('EMAIL_FROM', '')
    EMAIL_TO = os.getenv('EMAIL_TO', '').split(',') if os.getenv('EMAIL_TO') else []
    SMTP_SERVER = os.getenv('SMTP_SERVER', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() in ('true', '1', 't')
    
    # Telegram notification settings
    TELEGRAM_NOTIFICATIONS_ENABLED = os.getenv('TELEGRAM_NOTIFICATIONS_ENABLED', 'False').lower() in ('true', '1', 't')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '').split(',') if os.getenv('TELEGRAM_CHAT_ID') else []
    
    # Notification behavior settings
    NOTIFICATION_COOLDOWN_SECONDS = int(os.getenv('NOTIFICATION_COOLDOWN_SECONDS', '3600'))  # Default 1 hour
    DEVICE_OFFLINE_THRESHOLD_MINUTES = int(os.getenv('DEVICE_OFFLINE_THRESHOLD_MINUTES', '30'))
    
    # Cache configuration
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_THRESHOLD = int(os.getenv('CACHE_THRESHOLD', '1000'))
    # Specific cache TTLs for different endpoints
    DEVICE_CACHE_TTL = int(os.getenv('DEVICE_CACHE_TTL', '300'))  # Default 5 minutes for device data
    PLANT_CACHE_TTL = int(os.getenv('PLANT_CACHE_TTL', '600'))    # Default 10 minutes for plant data
    
    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # API settings
    API_RETRY_COUNT = int(os.getenv('API_RETRY_COUNT', '3'))
    API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', '2'))
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))  # Default 30 seconds timeout for API calls
    
    # Live reload for development
    LIVE_RELOAD_ENABLED = os.getenv('LIVE_RELOAD_ENABLED', 'False').lower() in ('true', '1', 't')
    
    # Environment-specific settings
    ENVIRONMENT = os.getenv('FLASK_ENV', 'production')
    
    # Background service settings
    ENABLE_BACKGROUND_MONITORING = os.getenv('ENABLE_BACKGROUND_MONITORING', 'True').lower() in ('true', '1', 't')
    MONITOR_DEVICE_STATUS = os.getenv('MONITOR_DEVICE_STATUS', 'True').lower() in ('true', '1', 't')
    COLLECT_DEVICE_DATA = os.getenv('COLLECT_DEVICE_DATA', 'True').lower() in ('true', '1', 't')
    COLLECT_PLANT_DATA = os.getenv('COLLECT_PLANT_DATA', 'True').lower() in ('true', '1', 't')
    DEVICE_STATUS_CHECK_INTERVAL_MINUTES = int(os.getenv('DEVICE_STATUS_CHECK_INTERVAL_MINUTES', '5'))
    DEVICE_DATA_CRON = os.getenv('DEVICE_DATA_CRON', '*/15 6-20 * * *')  # Every 15 mins from 6 AM to 8 PM
    PLANT_DATA_CRON = os.getenv('PLANT_DATA_CRON', '*/15 6-20 * * *')  # Every 15 mins from 6 AM to 8 PM
    USE_SQLALCHEMY_JOBSTORE = os.getenv('USE_SQLALCHEMY_JOBSTORE', 'False').lower() in ('true', '1', 't')
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    
    @classmethod
    def get_db_uri(cls) -> str:
        """Get the database URI based on configuration"""
        if cls.DATABASE_URL:
            # If a full DATABASE_URL is provided, use it directly
            return cls.DATABASE_URL
        
        # Build PostgreSQL connection string
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
    
    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """Get cache configuration dictionary for Flask-Caching"""
        return {
            'DEBUG': cls.DEBUG,
            'CACHE_TYPE': cls.CACHE_TYPE,
            'CACHE_DEFAULT_TIMEOUT': cls.CACHE_DEFAULT_TIMEOUT,
            'CACHE_THRESHOLD': cls.CACHE_THRESHOLD,
        }
    
    @classmethod
    def get_bool(cls, env_var: str, default: bool = False) -> bool:
        """Helper method to get boolean values from environment variables
        
        Args:
            env_var: Name of the environment variable
            default: Default value if environment variable is not set
            
        Returns:
            Boolean value of the environment variable
        """
        return os.getenv(env_var, str(default)).lower() in ('true', '1', 't', 'yes')
    
    @classmethod
    def get_int(cls, env_var: str, default: int = 0) -> int:
        """Helper method to get integer values from environment variables
        
        Args:
            env_var: Name of the environment variable
            default: Default value if environment variable is not set
            
        Returns:
            Integer value of the environment variable
        """
        try:
            return int(os.getenv(env_var, str(default)))
        except ValueError:
            return default
    
    @classmethod
    def get_float(cls, env_var: str, default: float = 0.0) -> float:
        """Helper method to get float values from environment variables
        
        Args:
            env_var: Name of the environment variable
            default: Default value if environment variable is not set
            
        Returns:
            Float value of the environment variable
        """
        try:
            return float(os.getenv(env_var, str(default)))
        except ValueError:
            return default
    
    @classmethod
    def get_str(cls, env_var: str, default: str = '') -> str:
        """Helper method to get string values from environment variables
        
        Args:
            env_var: Name of the environment variable
            default: Default value if environment variable is not set
            
        Returns:
            String value of the environment variable
        """
        return os.getenv(env_var, default)
