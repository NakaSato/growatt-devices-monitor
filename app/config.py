import os
import secrets
from datetime import timedelta

class Config:
    """Application configuration settings"""
    
    # Generate a random secret key if not provided in environment
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(16))
    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
    
    # Session configuration
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'False').lower() in ('true', '1', 't')
    SESSION_USE_SIGNER = os.getenv('SESSION_USE_SIGNER', 'True').lower() in ('true', '1', 't')
    PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600'))
    
    # Database path
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'app/data/growatt_data.db')
    
    # Growatt API credentials
    GROWATT_USERNAME = os.getenv('GROWATT_USERNAME')
    GROWATT_PASSWORD = os.getenv('GROWATT_PASSWORD')
    GROWATT_BASE_URL = os.getenv('GROWATT_BASE_URL', 'https://server.growatt.com')
    
    # Cache configuration
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_THRESHOLD = int(os.getenv('CACHE_THRESHOLD', '1000'))
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # API settings
    API_RETRY_COUNT = int(os.getenv('API_RETRY_COUNT', '3'))
    API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', '2'))
    
    @classmethod
    def get_db_uri(cls):
        """Get the database URI based on configuration"""
        return f"sqlite:///{cls.DATABASE_PATH}"