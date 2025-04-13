#!/usr/bin/env python3
"""
Utility script to set up a cron job for automatically syncing Growatt data
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from crontab import CronTab

def setup_cron_job(interval='hourly', user=None):
    """
    Set up a cron job to run data_sync.py at specified intervals
    
    Args:
        interval (str): Frequency interval ('hourly', 'daily', 'every6h', 'every12h')
        user (str): Username to set up cron job for (if None, uses current user)
    """
    # Get the current directory path where this script is located
    base_dir = Path(__file__).parent.absolute()
    
    # Paths to scripts
    sync_script_path = base_dir / "run_sync.sh"
    data_sync_path = base_dir / "data_sync.py"
    
    # Create the bash wrapper script if it doesn't exist
    if not sync_script_path.exists():
        with open(sync_script_path, 'w') as f:
            f.write(f'''#!/bin/bash
# Wrapper script to run data_sync.py with proper environment
cd {base_dir}
python3 {data_sync_path}
''')
        # Make it executable
        os.chmod(sync_script_path, 0o755)
        print(f"Created wrapper script at {sync_script_path}")
    
    # Ensure data_sync.py is executable
    os.chmod(data_sync_path, 0o755)
    
    # Initialize crontab for the specified user (or current user if not specified)
    cron = CronTab(user=user)
    
    # Remove any existing jobs for our script
    for job in cron.find_comment('Growatt API data sync'):
        cron.remove(job)
        print("Removed existing cron job")
    
    # Set up schedule based on interval
    job = cron.new(command=str(sync_script_path), comment='Growatt API data sync')
    
    if interval == 'hourly':
        job.hour.every(1)
        print("Setting up hourly sync")
    elif interval == 'every6h':
        job.hour.every(6)
        print("Setting up sync every 6 hours")
    elif interval == 'every12h':
        job.hour.every(12)
        print("Setting up sync every 12 hours")
    elif interval == 'daily':
        # Run once a day at 1:00 AM
        job.setall('0 1 * * *')
        print("Setting up daily sync at 1:00 AM")
    else:
        print(f"Unknown interval '{interval}'. Using hourly as default.")
        job.hour.every(1)
    
    # Write the crontab
    cron.write()
    
    print(f"Cron job set up successfully to run {sync_script_path} {interval}")
    print(f"Next run will be at {job.schedule().get_next()}")

def list_cron_jobs(user=None):
    """List all cron jobs for the specified user"""
    cron = CronTab(user=user)
    
    print("Current Growatt API cron jobs:")
    growatt_jobs = list(cron.find_comment('Growatt API data sync'))
    
    if not growatt_jobs:
        print("  No Growatt API cron jobs found")
    else:
        for i, job in enumerate(growatt_jobs, 1):
            print(f"  {i}. {job} (Next run: {job.schedule().get_next()})")

def remove_cron_jobs(user=None):
    """Remove all Growatt API cron jobs for the specified user"""
    cron = CronTab(user=user)
    
    removed = False
    for job in cron.find_comment('Growatt API data sync'):
        cron.remove(job)
        removed = True
    
    if removed:
        cron.write()
        print("All Growatt API cron jobs have been removed")
    else:
        print("No Growatt API cron jobs found to remove")

def main():
    """Main function to parse arguments and set up cron job"""
    parser = argparse.ArgumentParser(description='Set up cron job for Growatt API data sync')
    parser.add_argument('--interval', '-i', choices=['hourly', 'daily', 'every6h', 'every12h'], 
                       default='hourly', help='How often to run the sync (default: hourly)')
    parser.add_argument('--user', '-u', help='Username to set up cron for (default: current user)')
    parser.add_argument('--list', '-l', action='store_true', help='List current Growatt API cron jobs')
    parser.add_argument('--remove', '-r', action='store_true', help='Remove all Growatt API cron jobs')
    
    args = parser.parse_args()
    
    if args.list:
        list_cron_jobs(args.user)
    elif args.remove:
        remove_cron_jobs(args.user)
    else:
        setup_cron_job(args.interval, args.user)

if __name__ == "__main__":
    main()
