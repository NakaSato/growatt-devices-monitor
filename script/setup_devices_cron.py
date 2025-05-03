#!/usr/bin/env python3
"""
Cron Job Setup Script for Devices Data Collector

This script sets up a cron job to run the devices_data_collector.py script.
It can be configured to run every 5 minutes for 24 hours or only during daytime hours.
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/cron_setup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cron_setup")

def setup_cron_job(full_day=False):
    """
    Set up a cron job to run devices_data_collector.py every 5 minutes
    
    Args:
        full_day (bool): If True, run 24 hours; if False, run only from 6 AM to 8 PM
    """
    
    # Get the absolute path to the devices_data_collector.py script
    script_dir = Path(__file__).resolve().parent
    collector_script = script_dir / "devices_data_collector.py"
    
    if not collector_script.exists():
        logger.error(f"Collector script not found at {collector_script}")
        return False
    
    try:
        # Get current crontab content
        current_crontab = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode('utf-8')
    except subprocess.CalledProcessError:
        # No crontab exists yet
        current_crontab = ""
    
    # Check if our job is already in the crontab - remove it first
    old_cron_lines = []
    for line in current_crontab.splitlines():
        if str(collector_script) in line:
            old_cron_lines.append(line)
    
    # Remove any existing device collector jobs
    if old_cron_lines:
        for line in old_cron_lines:
            current_crontab = current_crontab.replace(line + "\n", "")
    
    # Create new cron line based on full_day flag
    if full_day:
        # Run every 5 minutes, 24/7
        cron_line = f"*/5 * * * * {collector_script}"
        schedule_desc = "24 hours"
    else:
        # Run every 5 minutes but only between 6 AM and 8 PM
        cron_line = f"*/5 6-20 * * * {collector_script}"
        schedule_desc = "between 6 AM and 8 PM"
    
    # Add our job to the crontab
    new_crontab = current_crontab
    if not new_crontab.endswith('\n'):
        new_crontab += '\n'
    new_crontab += f"{cron_line}\n"
    
    # Write the new crontab
    try:
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
        process.communicate(input=new_crontab.encode('utf-8'))
        if process.returncode == 0:
            logger.info(f"Successfully added cron job to run every 5 minutes {schedule_desc}")
            return True
        else:
            logger.error(f"Failed to update crontab, return code: {process.returncode}")
            return False
    except Exception as e:
        logger.error(f"Failed to update crontab: {e}")
        return False

def check_cron_job():
    """Check if the cron job is set up correctly"""
    try:
        # Get current crontab content
        current_crontab = subprocess.check_output(["crontab", "-l"]).decode('utf-8')
        
        # Get the absolute path to the devices_data_collector.py script
        script_dir = Path(__file__).resolve().parent
        collector_script = script_dir / "devices_data_collector.py"
        
        # Check if either of our patterns is in the crontab
        if str(collector_script) in current_crontab:
            logger.info("Cron job is set up (either full-day or daytime)")
            return True
        else:
            logger.warning("Cron job is not set up correctly")
            return False
    except subprocess.CalledProcessError:
        logger.warning("No crontab found")
        return False
    except Exception as e:
        logger.error(f"Failed to check crontab: {e}")
        return False

def remove_cron_job():
    """Remove the cron job for devices_data_collector.py"""
    try:
        # Get current crontab content
        current_crontab = subprocess.check_output(["crontab", "-l"]).decode('utf-8')
        
        # Get the absolute path to the devices_data_collector.py script
        script_dir = Path(__file__).resolve().parent
        collector_script = script_dir / "devices_data_collector.py"
        
        # Create new crontab without our job
        new_crontab = []
        for line in current_crontab.splitlines():
            if str(collector_script) not in line:
                new_crontab.append(line)
        
        new_crontab_str = '\n'.join(new_crontab) + '\n'
        
        # Write the new crontab
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
        process.communicate(input=new_crontab_str.encode('utf-8'))
        
        if process.returncode == 0:
            logger.info("Successfully removed cron job")
            return True
        else:
            logger.error(f"Failed to update crontab, return code: {process.returncode}")
            return False
    except subprocess.CalledProcessError:
        logger.warning("No crontab found")
        return True  # Consider it a success as there's no job to remove
    except Exception as e:
        logger.error(f"Failed to remove cron job: {e}")
        return False

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Set up or manage cron job for devices data collector')
    parser.add_argument('--check', action='store_true', help='Check if the cron job is set up correctly')
    parser.add_argument('--remove', action='store_true', help='Remove the cron job')
    parser.add_argument('--setup', action='store_true', help='Set up the cron job', default=True)
    parser.add_argument('--24h', dest='full_day', action='store_true', help='Run the collection 24 hours a day')
    
    args = parser.parse_args()
    
    # Ensure the logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    if args.check:
        if check_cron_job():
            print("Cron job is set up correctly.")
            sys.exit(0)
        else:
            print("Cron job is not set up correctly.")
            sys.exit(1)
    elif args.remove:
        if remove_cron_job():
            print("Cron job removed successfully.")
            sys.exit(0)
        else:
            print("Failed to remove cron job.")
            sys.exit(1)
    else:  # setup is default
        if setup_cron_job(args.full_day):
            if args.full_day:
                print("Cron job set up successfully. The collector will run every 5 minutes, 24 hours a day.")
            else:
                print("Cron job set up successfully. The collector will run every 5 minutes between 6 AM and 8 PM.")
            sys.exit(0)
        else:
            print("Failed to set up cron job.")
            sys.exit(1)

if __name__ == "__main__":
    main()