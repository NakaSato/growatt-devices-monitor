# Telegram Notifications for Growatt Devices Monitor

This document provides detailed instructions for setting up and using Telegram notifications with the Growatt Devices Monitor application.

## Overview

Telegram notifications allow you to receive real-time alerts about your Growatt devices, including:

- Device status changes (online/offline)
- Energy production updates
- System alerts
- Energy milestone notifications
- Weekly reports with charts

## Setup Instructions

### Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send the `/newbot` command to BotFather
3. Follow the instructions to create a new bot
   - Choose a name for your bot (e.g., "My Growatt Monitor")
   - Choose a username (must end with "bot", e.g., "MyGrowattMonitorBot")
4. BotFather will give you a token like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`
5. Save this token for later use

### Step 2: Get Your Chat ID

There are two ways to get your chat ID:

#### Option A: Using our setup script (recommended)

1. Run the `telegram_setup.py` script:
   ```bash
   python tests/telegram_setup.py
   ```
2. Follow the on-screen instructions:
   - Enter your bot token
   - Send a message to your bot on Telegram
   - The script will detect your chat ID and update your configuration

#### Option B: Manual setup

1. Start a chat with your bot
2. Send a message to your bot (any message will do)
3. Open this URL in your browser (replace `YOUR_BOT_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for the `"chat":{"id":` field in the response
5. This number is your chat ID (will be negative for group chats)

### Step 3: Update Configuration

Add the following to your `.env` file:

```
TELEGRAM_NOTIFICATIONS_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_NOTIFICATION_INTERVAL=30
```

For multiple chat IDs (to send to multiple users or groups), separate them with commas:

```
TELEGRAM_CHAT_ID=123456789,-987654321
```

### Step 4: Test Your Setup

Run the following command to test if your Telegram notifications are working:

```bash
python tests/test_telegram.py
```

You should receive a test message on Telegram. To test all notification features:

```bash
python tests/test_telegram_features.py
```

## Using Telegram Notifications

Once set up, Telegram notifications will be sent automatically based on your configuration:

- **Device Status Changes**: Get notified when devices go offline or come back online
- **Energy Production**: Regular updates about energy production
- **System Alerts**: Critical system issues or warnings
- **Energy Milestones**: Celebrations when you reach energy production milestones

### Manual Notifications

You can manually trigger notifications using:

```bash
python script/device_notification.py [--force]
```

The `--force` flag bypasses the cooldown period (useful for testing).

### Scheduled Notifications

Set up scheduled notifications using:

```bash
python script/setup_telegram_cron.py --install
```

This installs cron jobs to:

- Send hourly device status updates
- Send a daily summary at 8:00 AM

To list current notification cron jobs:

```bash
python script/setup_telegram_cron.py --list
```

To remove scheduled notifications:

```bash
python script/setup_telegram_cron.py --remove
```

## Advanced Features

### Customizing the Notification Cooldown

To avoid notification spam, there's a cooldown period between notifications for the same device. Adjust this in your `.env` file:

```
NOTIFICATION_COOLDOWN_SECONDS=3600  # Default is 1 hour
```

### Adding Custom Alerts

You can create custom alerts using the notification service. Here's an example:

```python
from app.services.notification_service import NotificationService

notification_service = NotificationService()
notification_service.send_system_alert(
    'info',
    'Solar production reached 15kWh today!',
    {'device': 'Inverter 1', 'time': '2:30 PM'}
)
```

### Multi-lingual Support

Telegram notifications support UTF-8 characters. You can customize your application to send notifications in different languages by modifying the message templates.

## Troubleshooting

### No Messages Received

1. Check that `TELEGRAM_NOTIFICATIONS_ENABLED` is set to `true`
2. Verify your bot token is correct by trying to message the bot
3. Make sure you've started a conversation with the bot
4. Check your chat ID is correct
5. Run the test script to verify configuration:
   ```bash
   python tests/test_telegram.py --debug
   ```

### Bot Not Responding

1. Make sure the bot is active by sending `/start` to it
2. Recreate the bot with BotFather if it remains unresponsive

### Message Format Issues

If your messages appear without formatting:

1. Check that your message is using valid HTML tags
2. Only certain HTML tags are supported by Telegram: `<b>`, `<i>`, `<code>`, `<pre>`, `<a>`

## Security Considerations

- Keep your bot token private; it can be used to control your bot
- For production environments, consider restricting which chat IDs can receive notifications
- Avoid sending sensitive information through Telegram notifications

## Further Reading

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [Growatt Devices Monitor Documentation](./INDEX_System.md)
