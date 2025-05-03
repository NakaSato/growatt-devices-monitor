#!/usr/bin/env python3
"""
Script to check the status of the Growatt background service.
This script will print the status of the scheduler and all scheduled jobs.
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path so we can import the app
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_background_service_status():
    """Check if the background service is running and display its status."""
    try:
        # Import the app and background service
        from app import create_app
        from app.services.background_service import background_service
        
        # Create app context
        app = create_app()
        
        with app.app_context():
            # Check if the service is running
            is_running = background_service.is_running()
            
            print("\n=== Background Service Status ===")
            print(f"Scheduler Running: {'Yes' if is_running else 'No'}")
            print(f"Initialized: {'Yes' if background_service.initialized else 'No'}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("===============================")
            
            if is_running:
                # Get all scheduled jobs
                jobs = background_service.get_jobs()
                
                if jobs:
                    print("\n=== Scheduled Jobs ===")
                    print(f"Total Jobs: {len(jobs)}")
                    
                    for i, job in enumerate(jobs, 1):
                        print(f"\nJob {i}: {job['name']} (ID: {job['id']})")
                        print(f"  Type: {job['type']}")
                        print(f"  Status: {'Active' if job['active'] else 'Paused'}")
                        print(f"  Next Run: {job['next_run']}")
                    
                    print("=====================")
                else:
                    print("\nNo scheduled jobs found.")
            
            return is_running
    except Exception as e:
        logger.error(f"Error checking background service status: {e}")
        print(f"\nError checking background service: {e}")
        return False

if __name__ == "__main__":
    is_running = check_background_service_status()
    sys.exit(0 if is_running else 1)