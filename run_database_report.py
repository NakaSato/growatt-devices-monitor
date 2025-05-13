#!/usr/bin/env python3
"""
Modified version of database_report.py with a fixed send_email function
"""
import os
import sys
import logging
import argparse

# Add the project root to the path so we can import the original module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the original database_report but don't execute its code
from scripts.reports import database_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a fixed version of the send_email function
def fixed_send_email(pdf_path, recipient):
    """
    Fixed version of send_email that handles both strings and lists
    """
    if isinstance(recipient, list):
        # Use the first email in the list if it's a list
        if recipient:
            recipient = recipient[0]
        else:
            logger.error("Empty recipient list provided")
            return False
    
    # Continue with the rest of the original function
    try:
        from app.config import Config
        
        # Check if email is enabled
        if not Config.EMAIL_NOTIFICATIONS_ENABLED:
            logger.error("Email notifications are not enabled in configuration")
            return False
            
        # Check if PDF exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file does not exist: {pdf_path}")
            return False
        
        # Log SMTP configuration for debugging
        smtp_server = Config.SMTP_SERVER
        smtp_port = Config.SMTP_PORT
        smtp_user = Config.SMTP_USERNAME
        smtp_use_tls = Config.SMTP_USE_TLS
        
        # Don't log the actual password, just whether it's set
        has_smtp_password = bool(Config.SMTP_PASSWORD)
        
        logger.info(f"SMTP Configuration: Server={smtp_server}, Port={smtp_port}, "
                   f"User={smtp_user}, TLS={smtp_use_tls}, Password set={has_smtp_password}")
        
        # Create message
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        import smtplib
        from datetime import datetime
        
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_FROM
        msg['To'] = recipient
        msg['Subject'] = f"Growatt Devices Status Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = """
        <html>
            <body>
                <h2>Growatt Devices Status Report</h2>
                <p>Please find attached the devices status report with data visualizations.</p>
                <p>This report includes device status information and energy production data.</p>
                <p>The report was automatically generated on {datetime}.</p>
                <p>Best regards,<br>
                Growatt Monitoring System</p>
            </body>
        </html>
        """.format(datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach PDF
        with open(pdf_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), _subtype='pdf')
            attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(attachment)
        
        # Connect to SMTP server and send email with detailed error handling
        try:
            logger.info(f"Connecting to SMTP server: {smtp_server}:{smtp_port}")
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                # Enable debug output for SMTP connection
                server.set_debuglevel(1)
                
                if smtp_use_tls:
                    logger.info("Starting TLS connection")
                    server.starttls()
                
                # Only attempt login if both username and password are provided
                if smtp_user and has_smtp_password:
                    logger.info(f"Logging in with username: {smtp_user}")
                    try:
                        server.login(smtp_user, Config.SMTP_PASSWORD)
                        logger.info("SMTP login successful")
                    except smtplib.SMTPAuthenticationError as auth_err:
                        if "Username and Password not accepted" in str(auth_err):
                            logger.error(f"SMTP authentication failed: {auth_err}")
                            logger.error("Gmail users: Make sure to use an App Password instead of your regular password. "
                                        "See https://support.google.com/accounts/answer/185833 for instructions.")
                        else:
                            logger.error(f"SMTP authentication error: {auth_err}")
                        return False
                
                logger.info(f"Sending email from {Config.EMAIL_FROM} to {recipient}")
                server.send_message(msg)
                logger.info("Email sent successfully")
            
            logger.info(f"Sent report email to {recipient}")
            return True
            
        except smtplib.SMTPConnectError as conn_err:
            logger.error(f"Failed to connect to SMTP server: {conn_err}")
            return False
        except smtplib.SMTPServerDisconnected as disc_err:
            logger.error(f"SMTP server disconnected: {disc_err}")
            return False
        except smtplib.SMTPException as smtp_err:
            logger.error(f"SMTP error: {smtp_err}")
            return False
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

# Replace the original send_email function with our fixed version
database_report.send_email = fixed_send_email

# Run the main function
if __name__ == "__main__":
    sys.exit(database_report.main())
