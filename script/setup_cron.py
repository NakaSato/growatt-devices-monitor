#!/usr/bin/env python3
"""
Setup script for Growatt API data synchronization cron jobs.
This script makes it easy to configure automatic data collection at different intervals.
"""

import os
import sys
import argparse
from pathlib import Path
from crontab import CronTab

# Constants
COMMENT_TAG = 'growatt-api-sync'
DEFAULT_INTERVAL = 'hourly'
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'script', 'data_sync.py')
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cron_sync.log')


def setup_cron_job(interval='hourly', user=None, log_path=None, list_only=False, remove=False):
    """
    Setup cron job for data synchronization
    
    Args:
        interval: Sync interval - 'every15m', 'hourly', 'daily', 'every6h', or 'every12h'
        user: Username for crontab (defaults to current user)
        log_path: Path to log file
        list_only: Only list current jobs, don't add new ones
        remove: Remove all growatt-api-sync jobs
        
    Returns:
        str: Status message
    """
    # Initialize crontab for the specified user
    cron = CronTab(user=user)
    
    # Handle list only option
    if list_only:
        return list_jobs(cron)
    
    # Handle remove option
    if remove:
        return remove_jobs(cron)
    
    # Validate script path
    if not os.path.exists(SCRIPT_PATH):
        return f"Error: Script not found at {SCRIPT_PATH}"
    
    # Make sure the script is executable
    os.chmod(SCRIPT_PATH, 0o755)
    
    # Construct log redirection if path is specified
    log_redirect = f" >> {log_path} 2>&1" if log_path else ""
    
    # Remove existing jobs with the same tag
    for job in cron.find_comment(COMMENT_TAG):
        cron.remove(job)
    
    # Create new job
    job = cron.new(comment=COMMENT_TAG)
    
    # Configure the job based on the interval
    if interval == 'every15m':
        job.setall('*/15 * * * *')  # Run every 15 minutes
        job.command = f"{sys.executable} {SCRIPT_PATH}{log_redirect}"
        msg = "Set up cron job to run every 15 minutes"
    elif interval == 'hourly':
        job.setall('0 * * * *')  # Run at the top of every hour
        job.command = f"{sys.executable} {SCRIPT_PATH}{log_redirect}"
        msg = "Set up cron job to run hourly"
    elif interval == 'every6h':
        job.setall('0 */6 * * *')  # Run every 6 hours
        job.command = f"{sys.executable} {SCRIPT_PATH}{log_redirect}"
        msg = "Set up cron job to run every 6 hours"
    elif interval == 'every12h':
        job.setall('0 */12 * * *')  # Run every 12 hours
        job.command = f"{sys.executable} {SCRIPT_PATH}{log_redirect}"
        msg = "Set up cron job to run every 12 hours"
    elif interval == 'daily':
        job.setall('0 1 * * *')  # Run at 1:00 AM
        job.command = f"{sys.executable} {SCRIPT_PATH}{log_redirect}"
        msg = "Set up cron job to run daily at 1:00 AM"
    else:
        return f"Error: Invalid interval '{interval}'"
    
    # Write the changes to crontab
    cron.write()
    
    return msg


def list_jobs(cron):
    """List all growatt API sync jobs"""
    jobs = list(cron.find_comment(COMMENT_TAG))
    if not jobs:
        return "No Growatt API sync jobs are currently scheduled"
    
    result = "Current Growatt API sync jobs:\n"
    for job in jobs:
        result += f"  {job}\n"
    
    return result


def remove_jobs(cron):
    """Remove all growatt API sync jobs"""
    count = 0
    for job in cron.find_comment(COMMENT_TAG):
        cron.remove(job)
        count += 1
    
    cron.write()
    
    if count == 0:
        return "No Growatt API sync jobs found to remove"
    else:
        return f"Removed {count} Growatt API sync job(s)"
    

def main():
    """Main function to set up cron job"""
    parser = argparse.ArgumentParser(description='Setup cron job for Growatt API data synchronization')
    
    # Options
    parser.add_argument('--interval', choices=['every15m', 'hourly', 'every6h', 'every12h', 'daily'], 
                        default=DEFAULT_INTERVAL, help='Sync interval')
    parser.add_argument('--user', help='Username for crontab (defaults to current user)')
    parser.add_argument('--log', default=LOG_PATH, help='Path to log file')
    parser.add_argument('--list', action='store_true', help='List current jobs')
    parser.add_argument('--remove', action='store_true', help='Remove all growatt-api-sync jobs')
    
    args = parser.parse_args()
    
    result = setup_cron_job(
        interval=args.interval,
        user=args.user,
        log_path=args.log,
        list_only=args.list,
        remove=args.remove
    )
    
    print(result)
    

if __name__ == '__main__':
    main()