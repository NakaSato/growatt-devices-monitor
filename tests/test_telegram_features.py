#!/usr/bin/env python3
"""
Test All Telegram Notification Features

This script tests all Telegram notification features:
1. Basic text messages
2. Device status notifications
3. Offline device notifications
4. Energy milestone notifications
5. System alert notifications
6. Photo messages

Usage:
    python test_telegram_features.py [--debug] [--skip-photo]
"""

import os
import sys
import logging
import argparse
import tempfile
from typing import Dict, Any, List
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Set up path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env files"""
    try:
        from dotenv import load_dotenv
        
        # Try to load from different potential locations
        env_paths = [
            '.env',                   # Root directory .env
            '.env.local',             # Local overrides
            'app/.env',               # App directory .env
            os.path.expanduser('~/.env.growatt')  # User-specific .env
        ]
        
        for env_path in env_paths:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                logger.info(f"Loaded environment from {env_path}")
                
    except ImportError as e:
        logger.warning(f"Failed to import dotenv: {e}")
    except Exception as e:
        logger.warning(f"Error loading environment variables: {e}")

def check_telegram_config():
    """
    Check if Telegram is properly configured
    
    Returns:
        tuple: (is_configured, notification_service)
    """
    try:
        from app.services.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        # Check if Telegram is configured
        if not notification_service.telegram_enabled:
            logger.error("Telegram notifications are not enabled in your config")
            print("Please set TELEGRAM_NOTIFICATIONS_ENABLED=true in your .env file")
            return False, None
            
        if not notification_service.telegram_bot_token:
            logger.error("Telegram bot token is not configured")
            print("Please set TELEGRAM_BOT_TOKEN in your .env file")
            return False, None
            
        if not notification_service.telegram_chat_id:
            logger.error("Telegram chat ID is not configured")
            print("Please set TELEGRAM_CHAT_ID in your .env file")
            return False, None
        
        return True, notification_service
        
    except ImportError as e:
        logger.error(f"Failed to import NotificationService: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error checking Telegram config: {e}")
        return False, None

def test_basic_message(notification_service):
    """Test sending a basic text message"""
    print("\n" + "="*80)
    print("Testing Basic Text Message".center(80))
    print("="*80)
    
    message = (
        "<b>🔔 Telegram Test Message 🔔</b>\n\n"
        "This is a basic test message from the Growatt Devices Monitor.\n"
        f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "<i>If you can see this, basic Telegram messaging is working!</i>"
    )
    
    success = notification_service._send_telegram(message)
    
    if success:
        print("✅ Basic text message sent successfully!")
    else:
        print("❌ Failed to send basic text message")
        
    return success

def test_device_offline_notification(notification_service):
    """Test sending a device offline notification"""
    print("\n" + "="*80)
    print("Testing Device Offline Notification".center(80))
    print("="*80)
    
    # Mock device data
    device_data = {
        'serial_number': 'TEST123456',
        'alias': 'Test Inverter',
        'plant_id': 'PLANT001',
        'plant_name': 'Test Solar Plant',
        'status': 'Offline',
        'last_update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Temporarily disable the cooldown to allow testing
    original_cooldown = notification_service.notification_cooldown
    notification_service.notification_cooldown = 0
    
    success = notification_service.send_device_offline_notification(device_data)
    
    # Restore original cooldown
    notification_service.notification_cooldown = original_cooldown
    
    if success:
        print("✅ Device offline notification sent successfully!")
    else:
        print("❌ Failed to send device offline notification")
        
    return success

def test_device_status_notification(notification_service):
    """Test sending a device status notification"""
    print("\n" + "="*80)
    print("Testing Device Status Notification".center(80))
    print("="*80)
    
    # Mock device data
    device_data = {
        'serial_number': 'TEST123456',
        'alias': 'Test Inverter',
        'plant_id': 'PLANT001',
        'plant_name': 'Test Solar Plant',
        'status': 'Normal',
        'last_update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'energy_today': '10.5',
        'energy_total': '1500.75'
    }
    
    # Temporarily disable the cooldown to allow testing
    original_cooldown = notification_service.notification_cooldown
    notification_service.notification_cooldown = 0
    
    success = notification_service.send_device_status_notification(device_data)
    
    # Restore original cooldown
    notification_service.notification_cooldown = original_cooldown
    
    if success:
        print("✅ Device status notification sent successfully!")
    else:
        print("❌ Failed to send device status notification")
        
    return success

def test_energy_milestone_notification(notification_service):
    """Test sending an energy milestone notification"""
    print("\n" + "="*80)
    print("Testing Energy Milestone Notification".center(80))
    print("="*80)
    
    # Mock device data
    device_data = {
        'serial_number': 'TEST123456',
        'alias': 'Test Inverter',
        'plant_id': 'PLANT001',
        'plant_name': 'Test Solar Plant',
        'energy_today': '15.2',
        'energy_total': '1500.0'
    }
    
    # Temporarily disable the cooldown to allow testing
    original_cooldown = notification_service.notification_cooldown
    notification_service.notification_cooldown = 0
    
    success = notification_service.send_energy_milestone_notification(device_data, 1500.0)
    
    # Restore original cooldown
    notification_service.notification_cooldown = original_cooldown
    
    if success:
        print("✅ Energy milestone notification sent successfully!")
    else:
        print("❌ Failed to send energy milestone notification")
        
    return success

def test_system_alert(notification_service):
    """Test sending a system alert notification"""
    print("\n" + "="*80)
    print("Testing System Alert Notification".center(80))
    print("="*80)
    
    # Mock details
    details = {
        'Component': 'Data Collector',
        'Error Code': 'API_ERROR_1001',
        'Last Success': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Retries': '3'
    }
    
    success = notification_service.send_system_alert(
        'warning',
        'Connection issues detected with the Growatt API. Attempting to reconnect.',
        details
    )
    
    if success:
        print("✅ System alert notification sent successfully!")
    else:
        print("❌ Failed to send system alert notification")
        
    return success

def create_sample_chart():
    """Create a sample energy production chart"""
    print("Creating sample energy chart...")
    
    # Create sample data
    dates = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    energy_values = [12.5, 14.2, 10.8, 15.6, 9.5, 16.2, 18.5]
    
    # Create figure and axis
    plt.figure(figsize=(10, 6))
    bars = plt.bar(dates, energy_values, color='#2ecc71')
    
    # Add labels and title
    plt.title('Weekly Energy Production (Test Data)', fontsize=16)
    plt.ylabel('Energy (kWh)', fontsize=12)
    plt.xlabel('Day of Week', fontsize=12)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                 f'{height} kWh', ha='center', va='bottom')
    
    # Add grid
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(temp_file.name, bbox_inches='tight')
    plt.close()
    
    print(f"Sample chart created at {temp_file.name}")
    return temp_file.name

def test_photo_message(notification_service):
    """Test sending a photo message"""
    print("\n" + "="*80)
    print("Testing Photo Message".center(80))
    print("="*80)
    
    # Create a sample chart
    chart_path = create_sample_chart()
    
    # Send photo message
    caption = (
        "<b>📊 Weekly Energy Production Report</b>\n\n"
        "This is a test chart showing sample energy production data.\n"
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    success = notification_service.send_telegram_photo(chart_path, caption)
    
    # Clean up temporary file
    try:
        os.unlink(chart_path)
    except Exception as e:
        logger.warning(f"Failed to delete temporary file {chart_path}: {e}")
    
    if success:
        print("✅ Photo message sent successfully!")
    else:
        print("❌ Failed to send photo message")
        
    return success

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test all Telegram notification features")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--skip-photo", action="store_true", help="Skip photo message test")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
    
    # Load environment variables
    load_environment()
    
    # Check Telegram configuration
    is_configured, notification_service = check_telegram_config()
    if not is_configured:
        return 1
    
    test_results = {}
    
    # Test basic message
    test_results['basic_message'] = test_basic_message(notification_service)
    
    # Test device offline notification
    test_results['device_offline'] = test_device_offline_notification(notification_service)
    
    # Test device status notification
    test_results['device_status'] = test_device_status_notification(notification_service)
    
    # Test energy milestone notification
    test_results['energy_milestone'] = test_energy_milestone_notification(notification_service)
    
    # Test system alert
    test_results['system_alert'] = test_system_alert(notification_service)
    
    # Test photo message (if not skipped)
    if not args.skip_photo:
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            test_results['photo_message'] = test_photo_message(notification_service)
        except ImportError:
            print("\n⚠️ Skipping photo test - matplotlib not installed")
            print("   To run this test, install matplotlib: pip install matplotlib")
            test_results['photo_message'] = None
    else:
        test_results['photo_message'] = None
    
    # Print summary
    print("\n" + "="*80)
    print("Test Results Summary".center(80))
    print("="*80)
    
    success_count = sum(1 for result in test_results.values() if result is True)
    failure_count = sum(1 for result in test_results.values() if result is False)
    skipped_count = sum(1 for result in test_results.values() if result is None)
    
    print(f"✅ Successes: {success_count}")
    print(f"❌ Failures: {failure_count}")
    print(f"⏭️ Skipped: {skipped_count}")
    
    for test_name, result in test_results.items():
        status = "✅ Passed" if result is True else "❌ Failed" if result is False else "⏭️ Skipped"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*80)
    
    if failure_count > 0:
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())
