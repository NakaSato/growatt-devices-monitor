#!/usr/bin/env python3
"""
This script fixes the email functionality in the Growatt Devices Monitor application.
It modifies the send_email function in database_report.py to properly handle email recipients in list format.
"""
import os
import sys
import re

# Path to the database_report.py file
db_report_path = "scripts/reports/database_report.py"

def fix_email_recipient_handling():
    """Fix the email recipient handling in the database_report.py file"""
    
    # Make sure the file exists
    if not os.path.exists(db_report_path):
        print(f"Error: {db_report_path} does not exist.")
        return False

    # Read the file content
    with open(db_report_path, 'r') as f:
        content = f.read()

    # Replace the recipient handling code
    old_recipient_code = """    # Process recipient (can be string or list)
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

    new_recipient_code = """    # Process recipient (can be string or list)
    # Convert string input that looks like a list to an actual list
    if isinstance(recipient, str) and recipient.startswith('[') and recipient.endswith(']'):
        try:
            # This handles cases where the recipient is a string like '["email@example.com"]'
            # Strip the outer quotes and brackets, then split by comma
            cleaned = recipient.strip('[]').replace('"', '').replace("'", "")
            recipient_list = [email.strip() for email in cleaned.split(',') if email.strip()]
            if recipient_list:
                recipient = recipient_list
            else:
                logger.error(f"Failed to parse recipient list from string: {recipient}")
        except Exception as e:
            logger.warning(f"Error parsing recipient string as list: {e}. Will treat as a regular string.")
    
    # Now handle the recipient appropriately based on its type
    if isinstance(recipient, list):
        if not recipient:
            logger.error("Empty recipient list provided")
            return False
        # For SMTP, we'll use all emails in the list
        email_recipients = recipient
        # For the 'To' header, join with commas
        email_recipient_header = ', '.join(recipient)
    else:
        email_recipients = [recipient]  # Convert to list for consistent handling
        email_recipient_header = recipient
        
    if not email_recipients:
        logger.error("No recipient email provided")
        return False"""

    content = content.replace(old_recipient_code, new_recipient_code)

    # Replace msg['To'] assignment
    old_to_assignment = """        msg['To'] = email_recipient"""
    new_to_assignment = """        msg['To'] = email_recipient_header"""
    
    content = content.replace(old_to_assignment, new_to_assignment)

    # Replace the send_message call
    old_send_pattern = r'logger.info\(f"Sending email from \{Config\.EMAIL_FROM\} to \{email_recipient\}"\)\s+server\.send_message\(msg\)'
    new_send_code = """                logger.info(f"Sending email from {Config.EMAIL_FROM} to {email_recipient_header}")
                
                # Send email to all recipients
                server.send_message(msg, from_addr=Config.EMAIL_FROM, to_addrs=email_recipients)"""
    
    content = re.sub(old_send_pattern, new_send_code, content)

    # Replace the success log message
    old_success_log = """            logger.info(f"Sent report email to {email_recipient}")"""
    new_success_log = """            logger.info(f"Sent report email to {email_recipient_header}")"""
    
    content = content.replace(old_success_log, new_success_log)

    # Write the modified content back to the file
    with open(db_report_path, 'w') as f:
        f.write(content)

    print(f"Successfully updated {db_report_path} to fix email recipient handling.")
    return True

def main():
    """Main function"""
    try:
        print("Fixing email recipient handling in database_report.py...")
        success = fix_email_recipient_handling()
        if success:
            print("Fix completed successfully!")
            return 0
        else:
            print("Fix failed.")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
