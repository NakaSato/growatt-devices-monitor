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
    
    # Database path
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'app/data/growatt_data.db')
    
    # Growatt API credentials
    GROWATT_USERNAME = os.getenv('GROWATT_USERNAME', '')
    GROWATT_PASSWORD = os.getenv('GROWATT_PASSWORD', '')
    GROWATT_BASE_URL = os.getenv('GROWATT_BASE_URL', 'https://server.growatt.com')
    
    # Cache configuration
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_THRESHOLD = int(os.getenv('CACHE_THRESHOLD', '1000'))
    
    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # API settings
    API_RETRY_COUNT = int(os.getenv('API_RETRY_COUNT', '3'))
    API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', '2'))
    
    # Live reload for development
    LIVE_RELOAD_ENABLED = os.getenv('LIVE_RELOAD_ENABLED', 'False').lower() in ('true', '1', 't')
    
    # Environment-specific settings
    ENVIRONMENT = os.getenv('FLASK_ENV', 'production')
    
    @classmethod
    def get_db_uri(cls) -> str:
        """Get the database URI based on configuration"""
        return f"sqlite:///{cls.DATABASE_PATH}"
    
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
