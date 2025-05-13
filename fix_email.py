#!/usr/bin/env python3
"""
Quick fix script to run the database report with email recipient handling
"""
import sys
import os
import logging
from scripts.reports.database_report import main as original_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fix the send_email function
import types
from scripts.reports import database_report

# Get original function
original_send_email = database_report.send_email

# Define new function
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
    
    return original_send_email(pdf_path, recipient)

# Replace the function
database_report.send_email = fixed_send_email

if __name__ == "__main__":
    # Run the original main function
    sys.exit(original_main())
