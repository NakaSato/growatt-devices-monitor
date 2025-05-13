#!/usr/bin/env python3
"""
Test script for the GitHub Action workflow

This script tests the basic functionality that would be run in the GitHub workflow
"""

import os
import sys
import logging

# Add the project root directory to the path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("workflow_test")

def main():
    """Test the imports and basic functionality that would be used in the GitHub workflow"""
    try:
        # Import app modules
        from app.config import Config
        from app.database import DatabaseConnector
        
        logger.info("Successfully imported app modules!")
        
        # Test basic database connection (if credentials are available)
        if hasattr(Config, 'POSTGRES_HOST') and Config.POSTGRES_HOST:
            logger.info(f"Database host: {Config.POSTGRES_HOST}")
            db = DatabaseConnector()
            logger.info("Successfully created database connector!")
        else:
            logger.info("No database configuration available for testing")
            
        return 0
    except Exception as e:
        logger.error(f"Error during test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
