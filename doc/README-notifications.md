# Growatt Devices Monitor

A monitoring and notification system for Growatt solar devices.

## Notification System

This project includes a comprehensive notification system that can alert you when your Growatt devices change status. The notification system supports:

- Email notifications
- Telegram notifications with rich features:
  - Device status updates
  - Offline device alerts
  - Energy production reports with charts
  - System alerts
  - Energy milestone celebrations

## Testing Telegram Notifications

To verify that your Telegram notification setup is working correctly, you can use the provided test scripts:

### Using test_telegram.py

This script tests basic Telegram notification functionality:

```bash
# Basic test
python tests/test_telegram.py

# With debug logging
python tests/test_telegram.py --debug
```

### Using test_telegram_features.py

To test all Telegram notification features:

```bash
# Test all features
python tests/test_telegram_features.py

# With debug logging
python tests/test_telegram_features.py --debug

# Skip photo/chart tests (if matplotlib not installed)
python tests/test_telegram_features.py --skip-photo
```

### Using telegram_setup.py

For a more interactive setup experience, use the setup script:

```
# Interactive setup
python tests/telegram_setup.py

# With debugging enabled
python tests/telegram_setup.py --debug

# Specify bot token directly
python tests/telegram_setup.py --token "YOUR_BOT_TOKEN"

# Specify both token and chat ID
python tests/telegram_setup.py --token "YOUR_BOT_TOKEN" --chat-id "YOUR_CHAT_ID"

# Skip waiting for messages if token/chat ID verification fails
python tests/telegram_setup.py --token "YOUR_BOT_TOKEN" --chat-id "YOUR_CHAT_ID" --no-wait
```

## Configuration

Telegram notification settings are stored in your `.env` file:

```
TELEGRAM_NOTIFICATIONS_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_NOTIFICATION_INTERVAL=30
```

For multiple receivers, separate chat IDs with commas:

```
TELEGRAM_CHAT_ID=123456789,-987654321
```

## Notification Service Features

The notification service supports:

- Multiple notification channels
- Cooldown periods to prevent notification spam
- HTML formatting for rich notifications
- Error handling and logging
- Photo and chart sharing
- Scheduled status reports

## Regular Notification Scripts

### Device Status Notifications

Send notifications about device status changes:

```bash
# Send device status notifications
python script/device_notification.py

# Force send (ignore cooldown periods)
python script/device_notification.py --force

# With debug logging
python script/device_notification.py --debug
```

### Energy Reports

Send energy production reports with charts:

```bash
# Daily report (last 24 hours)
python script/energy_report.py --daily

# Weekly report (last 7 days)
python script/energy_report.py --weekly

# Monthly report (last 30 days)
python script/energy_report.py --monthly
```

### Scheduled Notifications

Set up automated notifications via cron jobs:

```bash
# Install cron jobs for regular notifications
python script/setup_telegram_cron.py --install

# List current notification cron jobs
python script/setup_telegram_cron.py --list

# Remove notification cron jobs
python script/setup_telegram_cron.py --remove
```

## Troubleshooting

If you experience issues with notifications:

1. Verify your configuration in `.env`
2. Run the test script to check connectivity
3. Check log files for detailed error messages
4. Make sure your bot has permission to send messages to the specified chat

## Further Documentation

For a detailed guide on setting up and using Telegram notifications, see:

- [Telegram Notifications Documentation](./TELEGRAM_NOTIFICATIONS.md)

For more information, refer to the documentation in the `doc/` directory.
