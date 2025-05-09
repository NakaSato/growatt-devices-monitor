#!/usr/bin/env python3
"""
Test script for sending Telegram notifications
"""
import os
import sys
import logging
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

def main():
    """Test Telegram notifications"""
    try:
        # Load environment variables
        for env_file in ['.env', '.env.local']:
            if os.path.exists(env_file):
                load_dotenv(env_file)
                print(f"Loaded environment from {env_file}")
        
        # Import notification service
        from app.services.notification_service import NotificationService
        
        # Create notification service instance
        notification_service = NotificationService()
        
        # Check if Telegram is configured
        if not notification_service.telegram_enabled:
            print("Error: Telegram notifications are not enabled in your config")
            print("Please set TELEGRAM_NOTIFICATIONS_ENABLED=true in your .env file")
            return 1
            
        if not notification_service.telegram_bot_token:
            print("Error: Telegram bot token is not configured")
            print("Please set TELEGRAM_BOT_TOKEN in your .env file")
            return 1
            
        if not notification_service.telegram_chat_id:
            print("Error: Telegram chat ID is not configured")
            print("Please set TELEGRAM_CHAT_ID in your .env file")
            return 1
        
        # Prepare test message
        message = (
            "<b>🔔 Test Notification 🔔</b>\n\n"
            "This is a test message from the Growatt Devices Monitor.\n"
            "If you can see this, your Telegram notifications are working correctly.\n\n"
            f"<b>Current time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "<i>To fix notification issues, make sure your bot token and chat ID are correct.</i>"
        )
        
        # Send test message
        print("Sending test message via Telegram...")
        success = notification_service._send_telegram(message)
        
        if success:
            print("✅ Test message sent successfully!")
            print("Your Telegram notifications are working correctly.")
            return 0
        else:
            print("❌ Failed to send test message.")
            print("Please check your Telegram configuration in .env file.")
            return 1
            
    except Exception as e:
        logger.error(f"Error testing Telegram notifications: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
