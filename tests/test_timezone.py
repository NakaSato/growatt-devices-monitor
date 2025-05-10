#!/usr/bin/env python3
"""
Test script to verify timezone settings in the application.
This script will:
1. Print the current time in UTC and in Asia/Bangkok timezone
2. Initialize the app
3. Print the app's configured timezone
4. Print the scheduler's timezone
5. Display a scheduled job's next run time in both UTC and local time
"""

import os
import sys
import pytz
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_current_time():
    """Print the current time in UTC and in Asia/Bangkok timezone"""
    utc_now = datetime.now(pytz.UTC)
    bangkok_now = utc_now.astimezone(pytz.timezone('Asia/Bangkok'))
    
    print("=" * 50)
    print(f"Current UTC time:          {utc_now}")
    print(f"Current Asia/Bangkok time: {bangkok_now}")
    print(f"Time difference: {(bangkok_now.hour - utc_now.hour):+d} hours")
    print("=" * 50)

def main():
    """Main function to test timezone settings"""
    print("\nTesting Timezone Configuration:\n")
    
    # Step 1: Print current time in both UTC and Bangkok timezone
    print_current_time()
    
    # Step 2: Initialize the app
    from app import create_app
    app = create_app()
    
    # Step 3: Print the app's configured timezone
    with app.app_context():
        timezone_config = app.config.get('TIMEZONE', 'Not set')
        scheduler_timezone = app.config.get('SCHEDULER_TIMEZONE', 'Not set')
        
        print(f"\nApp Configuration:")
        print(f"TIMEZONE setting:          {timezone_config}")
        print(f"SCHEDULER_TIMEZONE setting: {scheduler_timezone}")
        
        # Step 4: Print the scheduler's timezone
        if hasattr(app, 'background_service') and app.background_service:
            scheduler = app.background_service.scheduler
            if scheduler:
                print(f"\nScheduler Configuration:")
                print(f"Scheduler timezone:        {scheduler.timezone}")
                
                # Step 5: Display job next run times
                print("\nScheduled Jobs and Their Next Run Times:")
                for job in scheduler.get_jobs():
                    job_id = job.id
                    next_run_utc = job.next_run_time
                    
                    if next_run_utc:
                        next_run_local = next_run_utc.astimezone(pytz.timezone('Asia/Bangkok'))
                        print(f"\nJob ID: {job_id}")
                        print(f"Next run (UTC):      {next_run_utc}")
                        print(f"Next run (Bangkok):  {next_run_local}")
                        
                        # Check if the times actually differ by the expected 7 hours
                        # The next_run_time might already be in the local timezone, so we need to check the timezone info
                        print(f"Next run timezone: {next_run_utc.tzinfo}")
                        
                        hour_diff = next_run_local.hour - next_run_utc.hour
                        if hour_diff < 0:  # Handle day crossing
                            hour_diff += 24
                            
                        print(f"Time difference: {hour_diff:+d} hours")
                        
                        # Check if the scheduled time is in the expected timezone
                        if str(next_run_utc.tzinfo) == 'Asia/Bangkok':
                            print("✅ Job is scheduled in correct timezone (Asia/Bangkok)")
                        elif hour_diff == 7:  # Bangkok is UTC+7
                            print("✅ Job appears to be correctly scheduled with a +7 hour difference")
                        else:
                            print("❌ WARNING: Job may not be using the correct timezone!")
            else:
                print("Scheduler is not initialized")
        else:
            print("Background service not available")

if __name__ == "__main__":
    main()
