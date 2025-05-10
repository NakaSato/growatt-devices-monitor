#!/usr/bin/env python3
"""
Advanced timezone test for Growatt Devices Monitor
This script will:
1. Create a test job that runs in 30 seconds
2. Print current times in UTC and Bangkok timezones
3. Wait for the job to execute
4. Verify that the job was executed at the expected time
"""

import os
import sys
import time
import pytz
import logging
from datetime import datetime, timedelta
from threading import Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Flags to track job execution
job_executed = Event()
execution_time_utc = None

def test_job():
    """Test job that will be executed by the scheduler"""
    global execution_time_utc
    execution_time_utc = datetime.now(pytz.UTC)
    logger.info(f"Test job executed at UTC: {execution_time_utc}")
    logger.info(f"Test job executed at Bangkok: {execution_time_utc.astimezone(pytz.timezone('Asia/Bangkok'))}")
    job_executed.set()

def main():
    """Main function to test timezone settings"""
    from app import create_app
    app = create_app()
    
    with app.app_context():
        background_service = app.background_service
        
        # Print timezone information
        print("\n" + "=" * 60)
        print("TIMEZONE TEST REPORT")
        print("=" * 60)
        
        utc_now = datetime.now(pytz.UTC)
        bangkok_now = utc_now.astimezone(pytz.timezone('Asia/Bangkok'))
        
        print(f"Current time (UTC):      {utc_now}")
        print(f"Current time (Bangkok):  {bangkok_now}")
        print(f"Time difference:         {(bangkok_now.hour - utc_now.hour):+d} hours")
        
        # Get app configuration
        timezone_config = app.config.get('TIMEZONE', 'Not set')
        scheduler_timezone = app.config.get('SCHEDULER_TIMEZONE', 'Not set')
        
        print("\nApplication Configuration:")
        print(f"TIMEZONE setting:          {timezone_config}")
        print(f"SCHEDULER_TIMEZONE setting: {scheduler_timezone}")
        
        # Get scheduler timezone
        scheduler = background_service.scheduler
        print(f"Scheduler timezone object:  {scheduler.timezone}")
        print(f"Scheduler timezone string:  {str(scheduler.timezone)}")
        
        # Add a test job to run in 30 seconds
        print("\nAdding test job to run in 30 seconds...")
        
        # Schedule a job for 30 seconds from now
        next_run = datetime.now(scheduler.timezone) + timedelta(seconds=30)
        
        # Convert to naive datetime as APScheduler expects
        if hasattr(next_run, 'replace'):
            # Use the scheduler's timezone
            next_run_naive = next_run.replace(tzinfo=None)
        else:
            # Fallback if we can't replace tzinfo
            next_run_naive = next_run
        
        from apscheduler.triggers.date import DateTrigger
        job = scheduler.add_job(
            test_job,
            trigger=DateTrigger(run_date=next_run, timezone=scheduler.timezone),
            id='timezone_test_job'
        )
        
        print(f"Job scheduled for: {job.next_run_time}")
        print(f"Job timezone info: {job.next_run_time.tzinfo}")
        
        # Wait for job to execute (with timeout)
        print("\nWaiting for job to execute (timeout: 60 seconds)...")
        job_executed_success = job_executed.wait(timeout=60)
        
        if job_executed_success:
            # Job was executed
            global execution_time_utc
            execution_time_bangkok = execution_time_utc.astimezone(pytz.timezone('Asia/Bangkok'))
            
            # Get expected time
            expected_time_bangkok = next_run.astimezone(pytz.timezone('Asia/Bangkok'))
            
            # Calculate difference in seconds
            time_diff = (execution_time_bangkok - expected_time_bangkok).total_seconds()
            
            print("\nJob Execution Results:")
            print(f"Expected execution (Bangkok): {expected_time_bangkok}")
            print(f"Actual execution (UTC):       {execution_time_utc}")
            print(f"Actual execution (Bangkok):   {execution_time_bangkok}")
            print(f"Time difference from expected: {time_diff:.2f} seconds")
            
            # Determine if the job was executed with the correct timezone
            if abs(time_diff) < 5:  # Allow 5 seconds of variance
                print("\n✅ SUCCESS: Job executed at the correct time in Bangkok timezone!")
            else:
                print("\n❌ FAILURE: Job did not execute at the expected time!")
        else:
            print("\n❌ FAILURE: Job did not execute within the timeout period!")
        
        # Clean up
        scheduler.remove_job('timezone_test_job')
        print("\nTest complete.")

if __name__ == "__main__":
    main()
