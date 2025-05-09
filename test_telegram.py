#!/usr/bin/env python3
"""
Test script for sending Telegram notifications

This script tests the Telegram notification functionality by:
1. Loading environment variables from .env files
2. Checking the Telegram configuration
3. Sending a test message via Telegram
4. Reporting the test results

Usage:
    python test_telegram.py [--debug]
"""
import os
import sys
import logging
import argparse
from typing import Tuple, Dict, Any
from dotenv import load_dotenv
from datetime import datetime

# Set up path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_environment() -> Dict[str, str]:
    """
    Load environment variables from .env files
    
    Returns:
        Dict[str, str]: Dictionary of loaded environment files
    """
    loaded_files = {}
    
    for env_file in ['.env', '.env.local']:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            loaded_files[env_file] = "Loaded"
            logger.debug(f"Loaded environment from {env_file}")
    
    return loaded_files

def check_telegram_config() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check if Telegram is properly configured
    
    Returns:
        Tuple[bool, str, Dict[str, Any]]: 
            - Success status
            - Error message if any
            - Config details dictionary
    """
    try:
        from app.services.notification_service import NotificationService
        notification_service = NotificationService()
        
        config_status = {
            "enabled": notification_service.telegram_enabled,
            "bot_token": bool(notification_service.telegram_bot_token),
            "chat_id": bool(notification_service.telegram_chat_id)
        }
        
        # Check if Telegram is configured
        if not notification_service.telegram_enabled:
            return False, "Telegram notifications are not enabled in your config", config_status
            
        if not notification_service.telegram_bot_token:
            return False, "Telegram bot token is not configured", config_status
            
        if not notification_service.telegram_chat_id:
            return False, "Telegram chat ID is not configured", config_status
        
        return True, "", {"notification_service": notification_service, **config_status}
        
    except ImportError as e:
        return False, f"Failed to import NotificationService: {e}", {}
    except Exception as e:
        return False, f"Unexpected error checking Telegram config: {e}", {}

def send_test_message(notification_service) -> Tuple[bool, str]:
    """
    Send a test message via Telegram
    
    Args:
        notification_service: NotificationService instance
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    try:
        # Prepare test message
        message = (
            "<b>🔔 Test Notification 🔔</b>\n\n"
            "This is a test message from the Growatt Devices Monitor.\n"
            "If you can see this, your Telegram notifications are working correctly.\n\n"
            f"<b>Current time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "<i>To fix notification issues, make sure your bot token and chat ID are correct.</i>"
        )
        
        # Send test message
        logger.info("Sending test message via Telegram...")
        success = notification_service._send_telegram(message)
        
        if success:
            return True, "Test message sent successfully! Your Telegram notifications are working correctly."
        else:
            return False, "Failed to send test message. Please check your Telegram configuration in .env file."
            
    except Exception as e:
        logger.error(f"Error sending Telegram test message: {e}")
        return False, f"Error sending test message: {e}"

def main():
    """
    Test Telegram notifications
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Telegram notifications")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
    
    try:
        # Load environment variables
        loaded_files = load_environment()
        if loaded_files:
            loaded_list = ", ".join(loaded_files.keys())
            print(f"Loaded environment from: {loaded_list}")
        else:
            print("Warning: No .env files found")
        
        # Check Telegram configuration
        config_ok, error_msg, config_details = check_telegram_config()
        if not config_ok:
            print(f"Error: {error_msg}")
            if "enabled" in config_details and not config_details["enabled"]:
                print("Please set TELEGRAM_NOTIFICATIONS_ENABLED=true in your .env file")
            if "bot_token" in config_details and not config_details["bot_token"]:
                print("Please set TELEGRAM_BOT_TOKEN in your .env file")
            if "chat_id" in config_details and not config_details["chat_id"]:
                print("Please set TELEGRAM_CHAT_ID in your .env file")
            return 1
        
        # Send test message
        print("Sending test message via Telegram...")
        success, message = send_test_message(config_details["notification_service"])
        
        # Report results
        if success:
            print(f"✅ {message}")
            return 0
        else:
            print(f"❌ {message}")
            return 1
            
    except Exception as e:
        logger.error(f"Error testing Telegram notifications: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
