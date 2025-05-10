#!/usr/bin/env python3
"""
Configuration Module for Growatt Devices Monitor Scripts

This module contains configuration settings for scripts.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import json
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Ensure necessary directories exist
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Default values
DEFAULT_SERVER_URL = os.getenv("GROWATT_SERVER_URL", "http://localhost:8000")
DEFAULT_DAYS_BACK = int(os.getenv("GROWATT_DEFAULT_DAYS_BACK", "7"))

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# API credentials
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")

# Database configuration
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME", str(BASE_DIR / "instance" / "growatt.db"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSL_MODE = os.getenv("DB_SSL_MODE", "disable")

def get_db_url() -> str:
    """
    Get database URL from environment variables
    
    Returns:
        str: Database URL
    """
    if DB_ENGINE == "sqlite":
        return f"sqlite:///{DB_NAME}"
    elif DB_ENGINE == "postgresql":
        return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        raise ValueError(f"Unsupported database engine: {DB_ENGINE}")

def get_telegram_config() -> Dict[str, str]:
    """
    Get Telegram configuration
    
    Returns:
        dict: Telegram configuration
    """
    return {
        "bot_token": TELEGRAM_BOT_TOKEN,
        "chat_id": TELEGRAM_CHAT_ID
    }

def load_config_file(filename: str) -> Optional[Dict[str, Any]]:
    """
    Load configuration from a JSON file
    
    Args:
        filename: Path to config file
        
    Returns:
        dict: Configuration from file, or None if file not found or invalid
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Failed to load config file {filename}: {str(e)}")
        return None

def save_config_file(config: Dict[str, Any], filename: str) -> bool:
    """
    Save configuration to a JSON file
    
    Args:
        config: Configuration to save
        filename: Path to config file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Failed to save config file {filename}: {str(e)}")
        return False 