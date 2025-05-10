#!/usr/bin/env python3
"""
Setup cron jobs for Telegram notifications

This script sets up, lists, or removes cron jobs for regular Telegram notifications.

Usage:
    python setup_telegram_cron.py --install
    python setup_telegram_cron.py --list
    python setup_telegram_cron.py --remove
"""

import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path
from crontab import CronTab
from datetime import datetime

# Configure logging
LOG_FILE = "logs/cron_setup.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_current_user():
    """Get the current username"""
    try:
        import getpass
        return getpass.getuser()
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        return None

def get_script_path(script_name):
    """Get the absolute path to a script in the script directory"""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Return the absolute path to the requested script
    return os.path.join(script_dir, script_name)

def install_cron_jobs():
    """Install cron jobs for Telegram notifications"""
    try:
        user = get_current_user()
        if not user:
            logger.error("Failed to determine current user. Cannot install cron jobs.")
            return False
            
        logger.info(f"Installing cron jobs for user: {user}")
        cron = CronTab(user=user)
        
        # Clear existing notification jobs to avoid duplicates
        remove_cron_jobs(silent=True)
        
        # Get paths to scripts
        device_notification_script = get_script_path("device_notification.py")
        energy_report_script = get_script_path("energy_report.py")
        
        # Check if scripts exist
        if not os.path.exists(device_notification_script):
            logger.error(f"Script not found: {device_notification_script}")
            return False
            
        if not os.path.exists(energy_report_script):
            logger.error(f"Script not found: {energy_report_script}")
            return False
            
        # Job 1: Hourly device status update
        hourly_job = cron.new(command=f"python {device_notification_script}")
        hourly_job.setall('0 * * * *')  # Run at the top of every hour
        hourly_job.set_comment("Growatt Monitor - Hourly device status update")
        
        # Job 2: Daily energy report
        daily_job = cron.new(command=f"python {energy_report_script} --daily")
        daily_job.setall('0 20 * * *')  # Run at 8:00 PM every day
        daily_job.set_comment("Growatt Monitor - Daily energy report")
        
        # Job 3: Weekly energy report
        weekly_job = cron.new(command=f"python {energy_report_script} --weekly")
        weekly_job.setall('0 18 * * 0')  # Run at 6:00 PM every Sunday
        weekly_job.set_comment("Growatt Monitor - Weekly energy report")
        
        # Job 4: Monthly energy report
        monthly_job = cron.new(command=f"python {energy_report_script} --monthly")
        monthly_job.setall('0 19 1 * *')  # Run at 7:00 PM on the 1st of each month
        monthly_job.set_comment("Growatt Monitor - Monthly energy report")
        
        # Write to crontab
        cron.write()
        
        logger.info("Successfully installed cron jobs:")
        logger.info("1. Hourly device status update (every hour)")
        logger.info("2. Daily energy report (8:00 PM daily)")
        logger.info("3. Weekly energy report (6:00 PM Sundays)")
        logger.info("4. Monthly energy report (7:00 PM on 1st of month)")
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import required module: {e}")
        logger.error("Please install python-crontab: pip install python-crontab")
        return False
    except Exception as e:
        logger.error(f"Failed to install cron jobs: {e}")
        return False

def list_cron_jobs(silent=False):
    """List currently installed cron jobs for Telegram notifications"""
    try:
        user = get_current_user()
        if not user:
            if not silent:
                logger.error("Failed to determine current user. Cannot list cron jobs.")
            return False
            
        cron = CronTab(user=user)
        
        # Filter jobs related to Growatt Monitor
        growatt_jobs = [job for job in cron if "Growatt Monitor" in job.comment]
        
        if not growatt_jobs:
            if not silent:
                logger.info("No Growatt Monitor notification jobs found.")
            return False
            
        if not silent:
            logger.info(f"Found {len(growatt_jobs)} Growatt Monitor notification jobs:")
            for i, job in enumerate(growatt_jobs, 1):
                logger.info(f"{i}. {job.comment}: {job}")
                
        return True
        
    except ImportError as e:
        if not silent:
            logger.error(f"Failed to import required module: {e}")
            logger.error("Please install python-crontab: pip install python-crontab")
        return False
    except Exception as e:
        if not silent:
            logger.error(f"Failed to list cron jobs: {e}")
        return False

def remove_cron_jobs(silent=False):
    """Remove all cron jobs for Telegram notifications"""
    try:
        user = get_current_user()
        if not user:
            if not silent:
                logger.error("Failed to determine current user. Cannot remove cron jobs.")
            return False
            
        cron = CronTab(user=user)
        
        # Count jobs before removal
        growatt_jobs = [job for job in cron if "Growatt Monitor" in job.comment]
        job_count = len(growatt_jobs)
        
        if job_count == 0:
            if not silent:
                logger.info("No Growatt Monitor notification jobs found to remove.")
            return False
            
        # Remove all jobs related to Growatt Monitor
        cron.remove_all(comment="Growatt Monitor - Hourly device status update")
        cron.remove_all(comment="Growatt Monitor - Daily energy report")
        cron.remove_all(comment="Growatt Monitor - Weekly energy report")
        cron.remove_all(comment="Growatt Monitor - Monthly energy report")
        
        # Write to crontab
        cron.write()
        
        if not silent:
            logger.info(f"Successfully removed {job_count} Growatt Monitor notification jobs.")
            
        return True
        
    except ImportError as e:
        if not silent:
            logger.error(f"Failed to import required module: {e}")
            logger.error("Please install python-crontab: pip install python-crontab")
        return False
    except Exception as e:
        if not silent:
            logger.error(f"Failed to remove cron jobs: {e}")
        return False
    
def check_crontab_access():
    """Check if the current user has access to crontab"""
    try:
        # Try to run crontab -l to check access
        subprocess.run(["crontab", "-l"], check=True, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to access crontab. Make sure you have permission to use crontab.")
        return False
    except Exception as e:
        logger.error(f"Error checking crontab access: {e}")
        return False

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Setup cron jobs for Telegram notifications")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="Install cron jobs")
    group.add_argument("--list", action="store_true", help="List installed cron jobs")
    group.add_argument("--remove", action="store_true", help="Remove all cron jobs")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        
    try:
        logger.info(f"Starting setup_telegram_cron.py at {datetime.now()}")
        
        # Check crontab access
        if not check_crontab_access():
            return 1
            
        # Perform requested action
        if args.install:
            logger.info("Installing cron jobs for Telegram notifications")
            if install_cron_jobs():
                logger.info("Cron jobs installed successfully")
                return 0
            else:
                logger.error("Failed to install cron jobs")
                return 1
                
        elif args.list:
            logger.info("Listing cron jobs for Telegram notifications")
            if list_cron_jobs():
                return 0
            else:
                return 1
                
        elif args.remove:
            logger.info("Removing cron jobs for Telegram notifications")
            if remove_cron_jobs():
                logger.info("Cron jobs removed successfully")
                return 0
            else:
                logger.error("Failed to remove cron jobs")
                return 1
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
        
if __name__ == "__main__":
    sys.exit(main())