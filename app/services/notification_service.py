import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Union, Tuple
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
        
        # Log initialization status
        self._log_initialization_status()
    
    def _log_initialization_status(self) -> None:
        """Log the initialization status of notification channels"""
        email_status = 'enabled' if self.email_enabled else 'disabled'
        telegram_status = 'enabled' if self.telegram_enabled else 'disabled'
        
        # Check if required configurations are present
        if self.email_enabled:
            if not all([self.smtp_server, self.smtp_port, self.email_from, self.email_to]):
                email_status += ' (incomplete configuration)'
                
        if self.telegram_enabled:
            if not all([self.telegram_bot_token, self.telegram_chat_id]):
                telegram_status += ' (incomplete configuration)'
                
        logger.info(f"Notification service initialized - Email: {email_status}, Telegram: {telegram_status}")
    
    
    def send_notification(self, message: str, subject: str = "Growatt Device Notification") -> bool:
        """
        General method to send notifications through all configured channels
        
        Args:
            message: Message content to send
            subject: Subject line for email notifications
            
        Returns:
            bool: True if at least one notification channel succeeded
        """
        if not self.email_enabled and not self.telegram_enabled:
            logger.warning("No notification channels enabled, skipping notification")
            return False
            
        success = False
        channels_attempted = 0
        channels_succeeded = 0
        
        # Try email notification
        if self.email_enabled:
            channels_attempted += 1
            email_success = self._send_email(subject, message)
            if email_success:
                channels_succeeded += 1
                success = True
        
        # Try Telegram notification
        if self.telegram_enabled:
            channels_attempted += 1
            telegram_success = self._send_telegram(message)
            if telegram_success:
                channels_succeeded += 1
                success = True
        
        # Log outcome
        if success:
            logger.info(f"Notification sent successfully via {channels_succeeded}/{channels_attempted} channels: '{subject}'")
        else:
            logger.warning(f"Failed to send notification via any channel (0/{channels_attempted}): '{subject}'")
            
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
        # Validate required fields
        serial_number = device_data.get('serial_number')
        if not serial_number:
            logger.error("Cannot send offline notification - missing serial_number")
            return False
            
        # Check if we're in cooldown period for this device
        now = datetime.now().timestamp()
        last_sent = self.last_notification_sent.get(serial_number, 0)
        cooldown_remaining = self.notification_cooldown - (now - last_sent)
        
        if now - last_sent < self.notification_cooldown:
            logger.debug(
                f"Skipping notification for device {serial_number} - "
                f"in cooldown period (remaining: {int(cooldown_remaining)}s)"
            )
            return False
        
        # Prepare notification content
        alias = device_data.get('alias', 'Unknown Device')
        plant_name = device_data.get('plant_name', 'Unknown Plant')
        last_seen = device_data.get('last_update_time', 'Unknown')
        
        # Prepare subject and message
        subject = f"⚠️ Device Offline: {alias} ({serial_number})"
        
        # Create HTML message with better formatting
        message = (
            f"<b>⚠️ Device Offline Alert</b><br><br>"
            f"<b>Device:</b> {alias}<br>"
            f"<b>Serial Number:</b> {serial_number}<br>"
            f"<b>Plant:</b> {plant_name}<br>"
            f"<b>Last Seen:</b> {last_seen}<br><br>"
            f"The device has gone offline and may require attention."
        )
        
        # Send notification
        notification_sent = self.send_notification(message, subject)
        
        # Update notification tracking
        if notification_sent:
            self.last_notification_sent[serial_number] = now
            logger.info(f"Offline notification sent for device {alias} ({serial_number})")
        else:
            logger.warning(f"Failed to send offline notification for device {alias} ({serial_number})")
        
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
        # Check if email is properly configured
        if not all([self.smtp_server, self.smtp_port, self.email_from, self.email_to]):
            logger.error("Email configuration is incomplete")
            return False
            
        try:
            # Create a multipart message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject
            
            # Attach message body - try to detect if HTML content and use appropriate MIME type
            if "<" in message and ">" in message:  # Simple check for HTML content
                msg.attach(MIMEText(message, 'html'))
            else:
                msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server with a timeout
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                # Use TLS if configured
                if self.smtp_use_tls:
                    server.starttls()
                
                # Login if credentials are provided
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                # Send the email
                server.send_message(msg)
            
            logger.info(f"Email sent successfully: '{subject}'")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except TimeoutError:
            logger.error("Timeout connecting to SMTP server")
            return False
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
        if not self.telegram_bot_token:
            logger.error("Telegram bot token is not configured")
            return False
            
        if not self.telegram_chat_id:
            logger.error("Telegram chat ID is not configured")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            # Handle chat_id as either a single value or a list
            chat_ids = self.telegram_chat_id
            
            # If chat_id is a list, send to all recipients
            if isinstance(chat_ids, list):
                if not chat_ids:  # Empty list
                    logger.error("No valid Telegram chat IDs found")
                    return False
                    
                success = False
                for chat_id in chat_ids:
                    if not chat_id:  # Skip empty chat IDs
                        continue
                        
                    success |= self._send_single_telegram_message(url, chat_id.strip(), message)
                
                return success
            else:
                # Handle single chat ID
                return self._send_single_telegram_message(url, chat_ids, message)
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
            
    def _send_single_telegram_message(self, url: str, chat_id: str, message: str) -> bool:
        """
        Send a Telegram message to a single chat ID
        
        Args:
            url: Telegram API URL
            chat_id: The chat ID to send the message to
            message: The message content
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'  # Using HTML mode which has fewer escaping requirements
            }
            
            # Add timeout to prevent hanging requests
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('ok'):
                    logger.info(f"Telegram message sent successfully to chat ID: {chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {response_data.get('description')}")
                    return False
            else:
                logger.error(f"Failed to send Telegram message to chat ID {chat_id}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Telegram request timed out for chat ID: {chat_id}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram request exception for chat ID {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message to chat ID {chat_id}: {e}")
            return False