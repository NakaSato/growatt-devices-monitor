"""
Growatt Devices Monitor Scripts Package

This package contains scripts for data collection, reporting, and notification for Growatt solar devices.
"""

import os
import sys
import logging

# Add parent directory to path so modules can be imported from the app
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(parent_dir))

# Configure basic logging
def configure_script_logging(name, level=logging.INFO):
    """Configure logging for scripts with console and file output"""
    # Ensure logs directory exists
    logs_dir = os.path.join(os.path.dirname(parent_dir), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicate logs
    if logger.handlers:
        logger.handlers.clear()
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(os.path.join(logs_dir, f'{name}.log'))
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger 