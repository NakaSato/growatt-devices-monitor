import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
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