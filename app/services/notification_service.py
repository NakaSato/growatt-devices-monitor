import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from app.config import Config

# Configure logging
logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications about device status changes"""
    
    def __init__(self):
        """Initialize the notification service with configuration"""
        # Email configuration
        self.email_enabled = Config.EMAIL_NOTIFICATIONS_ENABLED
        self.email_from = Config.EMAIL_FROM
        self.email_to = Config.EMAIL_TO
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.smtp_username = Config.SMTP_USERNAME
        self.smtp_password = Config.SMTP_PASSWORD
        self.smtp_use_tls = Config.SMTP_USE_TLS
        
        # Telegram configuration
        self.telegram_enabled = Config.TELEGRAM_NOTIFICATIONS_ENABLED
        self.telegram_bot_token = Config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = Config.TELEGRAM_CHAT_ID
        
        # Notification state management
        self.last_notification_sent = {}  # Track when notifications were last sent for each device
        self.notification_cooldown = Config.NOTIFICATION_COOLDOWN_SECONDS  # Cooldown period in seconds
        
        logger.info(
            f"Notification service initialized - Email: {'enabled' if self.email_enabled else 'disabled'}, "
            f"Telegram: {'enabled' if self.telegram_enabled else 'disabled'}"
        )
    
    def send_device_offline_notification(self, device_data: Dict[str, Any]) -> bool:
        """
        Send a notification that a device has gone offline
        
        Args:
            device_data: Dictionary containing device information
                - serial_number: Device serial number
                - alias: Device friendly name
                - plant_id: ID of the plant the device belongs to
                - plant_name: Name of the plant (if available)
                - status: Current device status
                - last_update_time: Last time the device was updated
                
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        serial_number = device_data.get('serial_number', 'Unknown')
        
        # Check if we're in cooldown period for this device
        now = datetime.now().timestamp()
        last_sent = self.last_notification_sent.get(serial_number, 0)
        
        if now - last_sent < self.notification_cooldown:
            logger.debug(f"Skipping notification for device {serial_number} - in cooldown period")
            return False
        
        # Prepare notification content
        alias = device_data.get('alias', 'Unknown Device')
        plant_name = device_data.get('plant_name', 'Unknown Plant')
        last_seen = device_data.get('last_update_time', 'Unknown')
        
        subject = f"🔴 Alert: Growatt Device Offline - {alias}"
        
        message = (
            f"⚠️ A Growatt device has gone OFFLINE ⚠️\n\n"
            f"Device: {alias}\n"
            f"Serial Number: {serial_number}\n"
            f"Plant: {plant_name}\n"
            f"Last Seen: {last_seen}\n\n"
            f"Please check the device status and connection."
        )
        
        success = False
        
        # Try to send email notification
        if self.email_enabled:
            email_success = self._send_email(subject, message)
            success = email_success
        
        # Try to send Telegram notification
        if self.telegram_enabled:
            telegram_success = self._send_telegram(message)
            success = success or telegram_success
        
        # Update last notification timestamp if any notification was successful
        if success:
            self.last_notification_sent[serial_number] = now
            logger.info(f"Offline notification sent for device {alias} ({serial_number})")
        
        return success
    
    def send_device_online_notification(self, device_data: Dict[str, Any]) -> bool:
        """
        Send a notification that a device has come back online
        
        Args:
            device_data: Dictionary containing device information
                - serial_number: Device serial number
                - alias: Device friendly name
                - plant_id: ID of the plant the device belongs to
                - plant_name: Name of the plant (if available)
                - status: Current device status
                - last_update_time: Last time the device was updated
                
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        serial_number = device_data.get('serial_number', 'Unknown')
        
        # Only send "back online" notifications if we previously sent an offline notification
        if serial_number not in self.last_notification_sent:
            logger.debug(f"Skipping online notification for device {serial_number} - no previous offline notification")
            return False
        
        # Check cooldown
        now = datetime.now().timestamp()
        last_sent = self.last_notification_sent.get(serial_number, 0)
        
        if now - last_sent < self.notification_cooldown:
            logger.debug(f"Skipping notification for device {serial_number} - in cooldown period")
            return False
        
        # Prepare notification content
        alias = device_data.get('alias', 'Unknown Device')
        plant_name = device_data.get('plant_name', 'Unknown Plant')
        last_seen = device_data.get('last_update_time', 'Unknown')
        
        subject = f"🟢 Growatt Device Back Online - {alias}"
        
        message = (
            f"✅ A Growatt device is back ONLINE ✅\n\n"
            f"Device: {alias}\n"
            f"Serial Number: {serial_number}\n"
            f"Plant: {plant_name}\n"
            f"Last Seen: {last_seen}\n\n"
            f"The device has reconnected and is now online."
        )
        
        success = False
        
        # Try to send email notification
        if self.email_enabled:
            email_success = self._send_email(subject, message)
            success = email_success
        
        # Try to send Telegram notification
        if self.telegram_enabled:
            telegram_success = self._send_telegram(message)
            success = success or telegram_success
        
        # Update last notification timestamp if any notification was successful
        if success:
            self.last_notification_sent[serial_number] = now
            logger.info(f"Online notification sent for device {alias} ({serial_number})")
            
        return success
    
    def _send_email(self, subject: str, message: str) -> bool:
        """
        Send an email notification
        
        Args:
            subject: Email subject
            message: Email message content
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.email_enabled or not all([self.email_from, self.email_to, self.smtp_server, self.smtp_port]):
            logger.warning("Email notifications disabled or missing configuration")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            
            # Handle multiple recipients
            if isinstance(self.email_to, list):
                msg['To'] = ', '.join(self.email_to)
            else:
                msg['To'] = self.email_to
                
            msg['Subject'] = subject
            
            # Attach message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server
            if self.smtp_use_tls:
                smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
                smtp.starttls()
            else:
                smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Login if credentials are provided
            if self.smtp_username and self.smtp_password:
                smtp.login(self.smtp_username, self.smtp_password)
            
            # Send email
            recipients = self.email_to if isinstance(self.email_to, list) else [self.email_to]
            smtp.sendmail(self.email_from, recipients, msg.as_string())
            smtp.quit()
            
            logger.debug(f"Email notification sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def _send_telegram(self, message: str) -> bool:
        """
        Send a Telegram notification
        
        Args:
            message: Message content to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.telegram_enabled or not all([self.telegram_bot_token, self.telegram_chat_id]):
            logger.warning("Telegram notifications disabled or missing configuration")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            # Handle multiple chat IDs
            chat_ids = self.telegram_chat_id
            if not isinstance(chat_ids, list):
                chat_ids = [chat_ids]
            
            success = False
            
            for chat_id in chat_ids:
                data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                
                response = requests.post(url, data=data, timeout=10)
                
                if response.status_code == 200:
                    logger.debug(f"Telegram notification sent to chat ID {chat_id}")
                    success = True
                else:
                    logger.error(f"Failed to send Telegram notification to {chat_id}: {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")
            return False
    
    def test_notification_channels(self) -> Dict[str, bool]:
        """
        Test all configured notification channels
        
        Returns:
            Dict[str, bool]: Dictionary with test results for each channel
        """
        results = {
            "email": False,
            "telegram": False
        }
        
        test_message = (
            f"🧪 This is a test notification from Growatt Devices Monitor\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"If you're receiving this, notifications are working correctly."
        )
        
        # Test email
        if self.email_enabled:
            subject = "Test Notification - Growatt Devices Monitor"
            results["email"] = self._send_email(subject, test_message)
        
        # Test Telegram
        if self.telegram_enabled:
            results["telegram"] = self._send_telegram(test_message)
        
        return results