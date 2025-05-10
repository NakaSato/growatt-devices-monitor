# Growatt Devices Monitor

A monitoring and notification system for Growatt solar devices.

## Notification System

This project includes a comprehensive notification system that can alert you when your Growatt devices change status. The notification system supports:

- Email notifications
- Telegram notifications

## Testing Telegram Notifications

To verify that your Telegram notification setup is working correctly, you can use the provided test scripts:

### Using test_telegram.py

This script tests the Telegram notification functionality:

```bash
# Basic test
python test_telegram.py

# With debug logging
python test_telegram.py --debug
```

### Using telegram_setup.py

For a more interactive setup experience, use the setup script:

```bash
# Interactive setup
python telegram_setup.py

# With debugging enabled
python telegram_setup.py --debug

# Specify bot token directly
python telegram_setup.py --token "YOUR_BOT_TOKEN"

# Specify both token and chat ID
python telegram_setup.py --token "YOUR_BOT_TOKEN" --chat-id "YOUR_CHAT_ID"

# Skip waiting for messages if token/chat ID verification fails
python telegram_setup.py --token "YOUR_BOT_TOKEN" --chat-id "YOUR_CHAT_ID" --no-wait
```

## Configuration

Telegram notification settings are stored in your `.env` file:

```
TELEGRAM_NOTIFICATIONS_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Notification Service Features

The notification service supports:

- Multiple notification channels
- Cooldown periods to prevent notification spam
- HTML formatting for rich notifications
- Error handling and logging

## Troubleshooting

If you experience issues with notifications:

1. Verify your configuration in `.env`
2. Run the test script to check connectivity
3. Check log files for detailed error messages
4. Make sure your bot has permission to send messages to the specified chat

For more information, refer to the documentation in the `doc/` directory.
