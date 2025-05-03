#!/usr/bin/env python3
"""
Setup Device Status Tracker Cron Job

This script sets up a cron job to run the device status tracker service
at regular intervals. The service tracks device status changes and
sends notifications when devices go offline or come back online.
"""

import os
import sys
import logging
import argparse
from crontab import CronTab
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cron_setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_script_path():
    """Get the absolute path to the device status service script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'device_status_service.py')

def check_cron_job(cron=None):
    """Check if the cron job for the device status service is set up correctly."""
    if cron is None:
        cron = CronTab(user=True)
    
    script_path = get_script_path()
    
    # Look for existing cron job
    for job in cron:
        if script_path in str(job) and 'device_status_service.py' in str(job):
            logger.info(f"Found existing cron job: {job}")
            return True
    
    logger.info("No device status service cron job found")
    return False

def remove_cron_job():
    """Remove the device status service cron job if it exists."""
    cron = CronTab(user=True)
    script_path = get_script_path()
    
    # Find and remove matching jobs
    jobs_removed = 0
    for job in cron:
        if script_path in str(job) and 'device_status_service.py' in str(job):
            cron.remove(job)
            jobs_removed += 1
    
    if jobs_removed > 0:
        cron.write()
        logger.info(f"Removed {jobs_removed} device status service cron job(s)")
        return True
    else:
        logger.info("No device status service cron jobs found to remove")
        return False

def setup_cron_job():
    """Set up a cron job to run the device status service every 5 minutes."""
    cron = CronTab(user=True)
    
    # Check if job already exists
    if check_cron_job(cron):
        logger.info("Cron job already exists, removing it first")
        for job in cron:
            if get_script_path() in str(job) and 'device_status_service.py' in str(job):
                cron.remove(job)
    
    # Create new cron job to run every 5 minutes
    job = cron.new(command=f'{get_script_path()} --once > logs/device_status_service.log 2>&1')
    job.minute.every(5)  # Run every 5 minutes
    
    # Add comment for identification
    job.set_comment('Growatt Device Status Tracker Service')
    
    # Write to crontab
    cron.write()
    logger.info(f"Cron job set up successfully: {job}")
    return True

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Set up or manage cron job for device status tracker')
    parser.add_argument('--check', action='store_true', help='Check if the cron job is set up correctly')
    parser.add_argument('--remove', action='store_true', help='Remove the cron job')
    parser.add_argument('--setup', action='store_true', help='Set up the cron job', default=True)
    
    args = parser.parse_args()
    
    # Ensure the logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    if args.check:
        if check_cron_job():
            print("Cron job for device status tracker is set up correctly.")
            sys.exit(0)
        else:
            print("Cron job for device status tracker is not set up correctly.")
            sys.exit(1)
    elif args.remove:
        if remove_cron_job():
            print("Cron job for device status tracker removed successfully.")
            sys.exit(0)
        else:
            print("Failed to remove cron job for device status tracker.")
            sys.exit(1)
    else:  # setup is default
        if setup_cron_job():
            print("Cron job set up successfully. The device status tracker will run every 5 minutes.")
            sys.exit(0)
        else:
            print("Failed to set up cron job for device status tracker.")
            sys.exit(1)

if __name__ == "__main__":
    main()