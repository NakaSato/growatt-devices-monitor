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
    
    def send_notification(self, message: str, subject: str = "Growatt Device Notification") -> bool:
        """
        General method to send notifications through all configured channels
        
        Args:
            message: Message content to send
            subject: Subject line for email notifications
            
        Returns:
            bool: True if at least one notification channel succeeded
        """
        success = False
        
        # Try email notification
        if self.email_enabled:
            email_success = self._send_email(subject, message)
            success = email_success
        
        # Try Telegram notification
        if self.telegram_enabled:
            telegram_success = self._send_telegram(message)
            success = success or telegram_success
        
        if success:
            logger.debug(f"Notification sent: {subject}")
        else:
            logger.warning(f"Failed to send notification: {subject}")
            
        return success
    
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
        
        subject = f"Device Offline: {alias} ({serial_number})"
        message = (
            f"Device '{alias}' ({serial_number}) belonging to plant '{plant_name}' "
            f"was last seen at {last_seen} and is now offline."
        )
        
        # Send notification
        notification_sent = self.send_notification(message, subject)
        
        if notification_sent:
            self.last_notification_sent[serial_number] = now
            logger.info(f"Offline notification sent for device {serial_number}")
        else:
            logger.warning(f"Failed to send offline notification for device {serial_number}")
        
        return notification_sent
    
    def _send_email(self, subject: str, message: str) -> bool:
        """
        Send an email notification
        
        Args:
            subject: Subject line for the email
            message: Message content for the email
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_telegram(self, message: str) -> bool:
        """
        Send a Telegram notification
        
        Args:
            message: Message content for the Telegram notification
            
        Returns:
            bool: True if at least one Telegram message was sent successfully, False otherwise
        """
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            # Handle chat_id as either a single value or a list
            chat_ids = self.telegram_chat_id
            
            # If chat_id is a list or comma-separated string, send to all recipients
            if isinstance(chat_ids, list):
                success = False
                for chat_id in chat_ids:
                    if not chat_id:  # Skip empty chat IDs
                        continue
                        
                    payload = {
                        'chat_id': chat_id.strip(),
                        'text': message
                    }
                    response = requests.post(url, json=payload)
                    
                    if response.status_code == 200:
                        logger.info(f"Telegram message sent successfully to chat ID: {chat_id}")
                        success = True
                    else:
                        logger.error(f"Failed to send Telegram message to chat ID {chat_id}: {response.text}")
                
                return success
            else:
                # Handle single chat ID
                payload = {
                    'chat_id': chat_ids,
                    'text': message
                }
                response = requests.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.info("Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Failed to send Telegram message: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False