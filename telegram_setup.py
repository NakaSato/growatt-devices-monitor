#!/usr/bin/env python3
"""
Telegram Bot Setup and Testing Script for Growatt Devices Monitor

This script helps to:
1. Verify Telegram bot token
2. Get the correct chat ID
3. Test sending messages
4. Update configuration
5. Troubleshoot common issues

Usage:
    python telegram_setup.py [--debug] [--token BOT_TOKEN] [--chat-id CHAT_ID] [--no-wait]
"""

# Standard library imports
import os
import sys
import logging
import time
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Union

# Third-party imports
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_bot_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify if a Telegram bot token is valid
    
    Args:
        token: The bot token to verify
        
    Returns:
        dict: Bot information if valid, None if invalid
    """
    if not token:
        logger.error("Bot token is empty")
        return None
        
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data.get('result')
            else:
                logger.error(f"Bot token invalid: {data.get('description')}")
                return None
        else:
            logger.error(f"HTTP error when checking bot token: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.Timeout:
        logger.error("Request timed out when checking bot token")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception when checking bot token: {e}")
        return None
    except Exception as e:
        logger.error(f"Exception when checking bot token: {e}")
        return None

def get_bot_updates(token: str, offset: Optional[int] = None, timeout: int = 30) -> Dict[str, Any]:
    """
    Get updates (messages) sent to the bot
    
    Args:
        token: The bot token
        offset: The offset to start getting updates from
        timeout: The timeout for long polling
        
    Returns:
        dict: JSON response containing updates
    """
    if not token:
        logger.error("Bot token is empty")
        return {'ok': False, 'description': 'Bot token is empty'}
    
    params = {
        'timeout': timeout,
    }
    
    if offset is not None:
        params['offset'] = offset
        
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates", 
            params=params,
            timeout=timeout + 5  # Add 5 seconds to the API timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"HTTP error when getting updates: {response.status_code} - {response.text}")
            return {'ok': False, 'description': f'HTTP error: {response.status_code}'}
    except requests.exceptions.Timeout:
        logger.error("Request timed out when getting updates")
        return {'ok': False, 'description': 'Request timed out'}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception when getting updates: {e}")
        return {'ok': False, 'description': f'Request exception: {e}'}
    except Exception as e:
        logger.error(f"Exception when getting updates: {e}")
        return {'ok': False, 'description': f'Exception: {e}'}

def send_test_message(token: str, chat_id: str, message: str = "Test message from Growatt Devices Monitor") -> bool:
    """
    Send a test message to a chat
    
    Args:
        token: The bot token
        chat_id: The chat ID to send the message to
        message: The message to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not token:
        logger.error("Bot token is empty")
        return False
        
    if not chat_id:
        logger.error("Chat ID is empty")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'  # Use HTML instead of Markdown to avoid escaping issues
        }
        
        # Add timeout to prevent hanging requests
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('ok'):
                logger.info("Test message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response_data.get('description')}")
                return False
        else:
            logger.error(f"Failed to send test message: HTTP {response.status_code} - {response.text}")
            return False
    except requests.exceptions.Timeout:
        logger.error("Request timed out when sending test message")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception when sending test message: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return False

def update_env_file(bot_token: str, chat_id: str) -> bool:
    """
    Update the .env file with the new Telegram configuration
    
    Args:
        bot_token: The bot token
        chat_id: The chat ID
        
    Returns:
        bool: True if the file was updated successfully, False otherwise
    """
    if not bot_token or not chat_id:
        logger.error("Bot token or chat ID is empty, cannot update .env file")
        return False
        
    try:
        env_path = Path('.env')
        env_backup_path = Path('.env.bak')
        
        # Create backup of existing .env file
        if env_path.exists():
            # Create backup
            import shutil
            shutil.copy2(env_path, env_backup_path)
            logger.info(f"Created backup of .env file at {env_backup_path}")
            
            with open(env_path, 'r') as f:
                lines = f.readlines()
                
            # Update or add Telegram settings
            telegram_enabled_found = False
            bot_token_found = False
            chat_id_found = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('TELEGRAM_NOTIFICATIONS_ENABLED='):
                    lines[i] = 'TELEGRAM_NOTIFICATIONS_ENABLED=true\n'
                    telegram_enabled_found = True
                elif line.startswith('TELEGRAM_BOT_TOKEN='):
                    lines[i] = f'TELEGRAM_BOT_TOKEN={bot_token}\n'
                    bot_token_found = True
                elif line.startswith('TELEGRAM_CHAT_ID='):
                    lines[i] = f'TELEGRAM_CHAT_ID={chat_id}\n'
                    chat_id_found = True
                    
            # Add settings if not found
            if not telegram_enabled_found:
                lines.append('TELEGRAM_NOTIFICATIONS_ENABLED=true\n')
            if not bot_token_found:
                lines.append(f'TELEGRAM_BOT_TOKEN={bot_token}\n')
            if not chat_id_found:
                lines.append(f'TELEGRAM_CHAT_ID={chat_id}\n')
                
            # Write back to .env
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
        else:
            # Create new .env file
            with open(env_path, 'w') as f:
                f.write('TELEGRAM_NOTIFICATIONS_ENABLED=true\n')
                f.write(f'TELEGRAM_BOT_TOKEN={bot_token}\n')
                f.write(f'TELEGRAM_CHAT_ID={chat_id}\n')
        
        logger.info(f"Updated .env file with Telegram configuration")
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        # Restore backup if it exists
        if env_path.exists() and env_backup_path.exists():
            try:
                import shutil
                shutil.copy2(env_backup_path, env_path)
                logger.info("Restored .env file from backup after error")
            except Exception as backup_error:
                logger.error(f"Failed to restore .env from backup: {backup_error}")
        return False

def show_instructions():
    """Display instructions for setting up Telegram bot"""
    print("\n" + "="*80)
    print("Telegram Bot Setup Instructions for Growatt Devices Monitor".center(80))
    print("="*80)
    
    print("\n1. Create a new Telegram bot:")
    print("   - Open Telegram app and search for @BotFather")
    print("   - Send /newbot command to BotFather")
    print("   - Follow the instructions to create a new bot")
    print("   - BotFather will give you a token like '123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ'")
    
    print("\n2. Configure your bot:")
    print("   - You need two pieces of information:")
    print("     a. Bot Token: provided by BotFather")
    print("     b. Chat ID: this script will help you get this")
    
    print("\n3. Add your bot to a group (optional):")
    print("   - Create a new group in Telegram")
    print("   - Add your bot to the group")
    print("   - Send a message to the group")
    print("   - This script will detect the group chat ID")
    
    print("\n4. Direct message to the bot:")
    print("   - Find your bot in Telegram and start a chat")
    print("   - Send a message to your bot")
    print("   - This script will detect your personal chat ID")
    
    print("\n5. Testing:")
    print("   - This script will send a test message to verify everything works")
    
    print("\n" + "="*80 + "\n")

def main():
    """Main function to set up and test Telegram bot"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Set up Telegram bot for Growatt Devices Monitor")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--token", type=str, help="Bot token to use (skips prompt)")
    parser.add_argument("--chat-id", type=str, help="Chat ID to use (skips prompt)")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for messages if chat ID is not provided")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        
    # Show setup instructions
    show_instructions()
    
    # Load environment variables
    load_dotenv()
    
    # Get existing token if available
    current_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    current_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Use command line token if provided
    if args.token:
        bot_token = args.token
        print(f"Using bot token from command line")
    else:
        # Prompt for bot token
        print(f"Current bot token: {current_token if current_token else 'Not set'}")
        bot_token = input("Enter your Telegram bot token (leave empty to keep current): ").strip()
        
    # Use current token if no new token provided
    if not bot_token and current_token:
        bot_token = current_token
        print(f"Using current bot token")
    
    if not bot_token:
        print("Bot token is required. Please run the script again and provide a valid token.")
        return 1
        
    # Verify the token
    print("\nVerifying bot token...")
    bot_info = check_bot_token(bot_token)
    if not bot_info:
        print("Invalid bot token. Please check the token and try again.")
        return 1
        
    print(f"Bot verified: @{bot_info.get('username')} - {bot_info.get('first_name')}")
    
    # Use command line chat ID if provided
    if args.chat_id:
        chat_id = args.chat_id
        print(f"Using chat ID from command line: {chat_id}")
        
        # Test sending a message with the provided chat ID
        print("\nSending test message with provided chat ID...")
        if send_test_message(bot_token, chat_id, f"Test message from Growatt Devices Monitor setup script\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"):
            print("Test message sent successfully. Your Telegram setup is working!")
            update_env_file(bot_token, chat_id)
            return 0
        else:
            print("Failed to send test message with provided chat ID.")
            if args.no_wait:
                print("Exiting without further attempts.")
                return 1
    # Check if we already have a chat ID
    elif current_chat_id:
        print(f"\nCurrent chat ID: {current_chat_id}")
        use_current = input("Use this chat ID? (y/n): ").strip().lower()
        if use_current == 'y':
            chat_id = current_chat_id
            # Test sending a message with the existing chat ID
            print("\nSending test message with existing chat ID...")
            if send_test_message(bot_token, chat_id, f"Test message from Growatt Devices Monitor setup script\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"):
                print("Test message sent successfully. Your Telegram setup is working!")
                # Update .env file
                update_env_file(bot_token, chat_id)
                return
            else:
                print("Failed to send test message with existing chat ID. Let's try to get a new one.")
        
    # Get chat ID
    print("\nWaiting for you to send a message to the bot...")
    print(f"Please send a message to @{bot_info.get('username')} on Telegram")
    print("(Press Ctrl+C to cancel)")
    
    last_update_id = None
    max_wait_time = 300  # 5 minutes timeout
    start_time = time.time()
    
    try:
        while time.time() - start_time < max_wait_time:
            updates = get_bot_updates(bot_token, offset=last_update_id)
            
            if updates.get('ok', False) and updates.get('result'):
                for update in updates['result']:
                    # Record the update ID to avoid processing the same update twice
                    last_update_id = update['update_id'] + 1
                    
                    # Check if this is a message update
                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        chat_type = message['chat']['type']
                        
                        if 'text' in message:
                            print(f"\nReceived message from a {chat_type}!")
                            if chat_type == 'private':
                                print(f"Chat ID (personal): {chat_id}")
                                print(f"From: {message['from'].get('first_name', '')} {message['from'].get('last_name', '')}")
                            else:
                                print(f"Chat ID (group): {chat_id}")
                                print(f"Group: {message['chat'].get('title', '')}")
                                
                            # Ask if this is the chat ID they want to use
                            use_this_chat = input("\nUse this chat for notifications? (y/n): ").strip().lower()
                            if use_this_chat == 'y':
                                # Test sending a message
                                print("\nSending test message...")
                                test_result = send_test_message(
                                    bot_token, 
                                    chat_id, 
                                    f"Test message from Growatt Devices Monitor setup script\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                )
                                
                                if test_result:
                                    print("Test message sent successfully!")
                                    
                                    # Update .env file
                                    print("\nUpdating configuration...")
                                    if update_env_file(bot_token, chat_id):
                                        print("\nTelegram setup completed successfully!")
                                        print(f"Bot: @{bot_info.get('username')}")
                                        print(f"Chat ID: {chat_id}")
                                        print("\nYour notifications should now work correctly.")
                                        return 0
                                else:
                                    print("Failed to send test message. Please try again with a different chat.")
                            
                            # Continue waiting for more messages if the user didn't choose this chat
                            print("Continuing to wait for messages...")
            
            # Sleep to avoid hitting rate limits
            time.sleep(2)
            
        # If we hit the timeout
        print("\nTimed out waiting for messages. Please run the script again when you're ready to send a message to the bot.")
        return 1
            
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\nError during setup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())