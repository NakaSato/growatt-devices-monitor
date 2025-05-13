#!/usr/bin/env python3
"""
Improved email handling for Growatt devices monitor

This script provides a more robust implementation for handling email recipients 
in both database_report.py files (in scripts/reports and scripts/database).
It ensures both string and list recipients are properly handled.
"""
import os
import sys
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths to the files we need to modify
REPORTS_PATH = "scripts/reports/database_report.py"
DATABASE_PATH = "scripts/database/database_report.py"

def fix_reports_email_function():
    """Fix the email function in the reports module"""
    
    logger.info(f"Fixing email function in {REPORTS_PATH}")
    
    with open(REPORTS_PATH, 'r') as f:
        content = f.read()
    
    # Fix imports if needed
    if "from typing import" in content and "Union" not in content:
        # Add Union to the imports
        content = re.sub(
            r'from typing import (.*)',
            r'from typing import \1, Union',
            content
        )
    
    # Fix the function signature
    content = content.replace(
        "def send_email(pdf_path: str, recipient) -> bool:",
        "def send_email(pdf_path: str, recipient: Union[str, List[str]]) -> bool:"
    )
    
    # Improve the function implementation for handling list recipients
    old_recipient_code = """    # Convert recipient to string if it's a list
    if isinstance(recipient, list):
        recipient = recipient[0] if recipient else ""
    
    if not recipient:
        logger.error("No recipient email provided")
        return False"""
        
    new_recipient_code = """    # Process recipient (can be string or list)
    if isinstance(recipient, list):
        if not recipient:
            logger.error("Empty recipient list provided")
            return False
        # Use the first email in the list
        email_recipient = recipient[0]
    else:
        email_recipient = recipient
        
    if not email_recipient:
        logger.error("No recipient email provided")
        return False"""
    
    content = content.replace(old_recipient_code, new_recipient_code)
    
    # Replace all occurrences of recipient with email_recipient in the msg code
    content = re.sub(
        r"msg\['To'\] = recipient",
        r"msg['To'] = email_recipient",
        content
    )
    
    # Replace all occurrences in log messages
    content = re.sub(
        r'logger\.info\(f"Sending email from \{Config\.EMAIL_FROM\} to \{recipient\}"\)',
        r'logger.info(f"Sending email from {Config.EMAIL_FROM} to {email_recipient}")',
        content
    )
    
    content = re.sub(
        r'logger\.info\(f"Sent report email to \{recipient\}"\)',
        r'logger.info(f"Sent report email to {email_recipient}")',
        content
    )
    
    # Write the updated content back to the file
    with open(REPORTS_PATH, 'w') as f:
        f.write(content)
    
    logger.info(f"Successfully updated {REPORTS_PATH}")
    return True

def fix_database_email_function():
    """Fix the email function in the database module if needed"""
    
    logger.info(f"Checking email function in {DATABASE_PATH}")
    
    with open(DATABASE_PATH, 'r') as f:
        content = f.read()
    
    # Check if the function is already correct
    if "email_recipient = recipient[0] if isinstance(recipient, list) and recipient else recipient" in content:
        logger.info(f"Email function in {DATABASE_PATH} already has correct implementation")
        return True
    
    # If not, apply similar fixes as for the reports module
    old_recipient_code = """        # Convert recipient to string if it's a list
        email_recipient = recipient[0] if isinstance(recipient, list) and recipient else recipient"""
        
    new_recipient_code = """        # Process recipient (can be string or list)
        if isinstance(recipient, list):
            if not recipient:
                logger.error("Empty recipient list provided")
                return False
            # Use the first email in the list
            email_recipient = recipient[0]
        else:
            email_recipient = recipient
            
        if not email_recipient:
            logger.error("No recipient email provided")
            return False"""
    
    content = content.replace(old_recipient_code, new_recipient_code)
    
    # Write the updated content back to the file
    with open(DATABASE_PATH, 'w') as f:
        f.write(content)
    
    logger.info(f"Successfully updated {DATABASE_PATH}")
    return True

def main():
    """Main function"""
    try:
        success_reports = fix_reports_email_function()
        success_database = fix_database_email_function()
        
        if success_reports and success_database:
            logger.info("Successfully updated both database_report.py files")
            
            # Run a test to verify the fix
            logger.info("Running a test to verify the fix...")
            os.system("python3 scripts/reports/database_report.py --email enwuft@gmail.com")
            
            return 0
        else:
            logger.error("Failed to update one or both files")
            return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
