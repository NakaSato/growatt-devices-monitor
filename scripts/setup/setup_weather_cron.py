#!/usr/bin/env python3
"""
Setup Cron Job for Weather Data Collection

This script sets up a cron job to regularly collect weather data for solar plants.
Weather data is important for analyzing and predicting solar energy production.

Usage:
    python setup_weather_cron.py [--interval HOURS] [--days DAYS]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from crontab import CronTab

# Add parent directory to path to make app module importable
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_weather_cron(interval_hours=6, days=3, user=None):
    """
    Set up a cron job to collect weather data at regular intervals
    
    Args:
        interval_hours: Interval in hours between weather data collections
        days: Number of days of weather data to collect
        user: Username for the cron job
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current user if not specified
        if user is None:
            import getpass
            user = getpass.getuser()
            
        logger.info(f"Setting up weather data collection cron job for user: {user}")
        
        # Initialize crontab for the user
        cron = CronTab(user=user)
        
        # Define command to run
        script_path = os.path.abspath(os.path.join(parent_dir, "script", "collect_weather_data.py"))
        python_path = sys.executable
        log_path = os.path.join(parent_dir, "logs", "weather_cron.log")
        
        # Ensure script is executable
        if not os.access(script_path, os.X_OK):
            os.chmod(script_path, 0o755)
        
        # Create command
        command = f"{python_path} {script_path} --days {days} >> {log_path} 2>&1"
        
        # Check if the job already exists
        existing_job = None
        for job in cron:
            if script_path in str(job):
                existing_job = job
                break
        
        if existing_job:
            # Update existing job
            logger.info(f"Updating existing cron job: {existing_job}")
            existing_job.setall(f"0 */{interval_hours} * * *")  # Every n hours
            existing_job.command = command
        else:
            # Create new job
            logger.info(f"Creating new cron job to run every {interval_hours} hours")
            job = cron.new(command=command)
            job.setall(f"0 */{interval_hours} * * *")  # Every n hours
        
        # Save crontab
        cron.write()
        
        logger.info(f"Cron job set up successfully. Command: {command}")
        
        # Print next run time
        next_run = job.schedule(date_from=None).get_next()
        logger.info(f"Next scheduled run: {next_run}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up cron job: {str(e)}")
        return False

def remove_weather_cron(user=None):
    """
    Remove the weather data collection cron job
    
    Args:
        user: Username for the cron job
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current user if not specified
        if user is None:
            import getpass
            user = getpass.getuser()
            
        logger.info(f"Removing weather data collection cron job for user: {user}")
        
        # Initialize crontab for the user
        cron = CronTab(user=user)
        
        # Find script path
        script_path = os.path.abspath(os.path.join(parent_dir, "script", "collect_weather_data.py"))
        
        # Find and remove job
        removed = False
        for job in cron:
            if script_path in str(job):
                cron.remove(job)
                removed = True
        
        if removed:
            # Save crontab
            cron.write()
            logger.info("Cron job removed successfully")
        else:
            logger.info("No matching cron job found")
        
        return True
        
    except Exception as e:
        logger.error(f"Error removing cron job: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Setup cron job for weather data collection")
    parser.add_argument("--interval", type=int, default=6, help="Interval in hours between collections")
    parser.add_argument("--days", type=int, default=3, help="Number of days of weather data to collect")
    parser.add_argument("--user", type=str, help="Username for cron job (default: current user)")
    parser.add_argument("--remove", action="store_true", help="Remove existing cron job")
    args = parser.parse_args()
    
    if args.remove:
        result = remove_weather_cron(user=args.user)
    else:
        result = setup_weather_cron(
            interval_hours=args.interval,
            days=args.days,
            user=args.user
        )
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main()) 