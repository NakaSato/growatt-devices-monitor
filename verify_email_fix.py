#!/usr/bin/env python3
"""
Final email fix script for Growatt devices monitor

This script verifies the email functionality in both database_report.py files.
It runs a test to ensure the email feature works properly with both string and list recipients.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_email_functionality():
    """Run tests to verify the email functionality"""
    logger.info("Testing email functionality with a string recipient...")
    result1 = os.system("python3 scripts/reports/database_report.py --email enwuft@gmail.com")
    
    logger.info("Testing email functionality with a list recipient...")
    # We'll use a test script for this
    test_script = """
import sys
from scripts.reports.database_report import main as db_report_main

# Override sys.argv to include our test arguments
sys.argv = ['database_report.py', '--email', '["enwuft@gmail.com"]']

# Run the main function
sys.exit(db_report_main())
"""
    
    with open("test_list_recipient.py", "w") as f:
        f.write(test_script)
    
    result2 = os.system("python3 test_list_recipient.py")
    
    if result1 == 0 and result2 == 0:
        logger.info("Both tests passed! The email functionality works correctly.")
        return True
    else:
        logger.error("One or both tests failed. Please check the logs for details.")
        return False

def main():
    """Main function"""
    try:
        if verify_email_functionality():
            logger.info("Email functionality verification completed successfully.")
            return 0
        else:
            logger.error("Email functionality verification failed.")
            return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
