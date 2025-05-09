#!/usr/bin/env python3
"""
Final timezone verification for Growatt Devices Monitor

This script prints timezone information and confirms all scheduled jobs are
using the Asia/Bangkok timezone. It also checks actual job execution.
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

# Flag to track job execution
job_executed = Event()
execution_time = None

def test_job():
    """Test job that will be executed by the scheduler"""
    global execution_time
    execution_time = datetime.now(pytz.timezone('Asia/Bangkok'))
    logger.info(f"Test job executed at Bangkok time: {execution_time}")
    job_executed.set()

def main():
    """Main function to verify timezone settings"""
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Print header
        print("\n" + "=" * 60)
        print("TIMEZONE VERIFICATION REPORT")
        print("=" * 60)
        
        # Print current times
        utc_now = datetime.now(pytz.UTC)
        bangkok_now = utc_now.astimezone(pytz.timezone('Asia/Bangkok'))
        print(f"Current UTC time:          {utc_now}")
        print(f"Current Asia/Bangkok time: {bangkok_now}")
        print(f"Time difference: {(bangkok_now.hour - utc_now.hour):+d} hours")
        
        # Get application timezone settings
        print("\nAPPLICATION TIMEZONE SETTINGS:")
        timezone_config = app.config.get('TIMEZONE', 'Not set')
        scheduler_timezone = app.config.get('SCHEDULER_TIMEZONE', 'Not set')
        print(f"TIMEZONE setting:           {timezone_config}")
        print(f"SCHEDULER_TIMEZONE setting: {scheduler_timezone}")
        
        # Get scheduler timezone
        scheduler = app.background_service.scheduler
        print(f"Actual scheduler timezone:  {scheduler.timezone}")
        
        # Verify existing jobs
        print("\nEXISTING SCHEDULED JOBS:")
        all_correct = True
        for job in scheduler.get_jobs():
            job_id = job.id
            next_run = job.next_run_time
            timezone_name = str(next_run.tzinfo) if next_run and next_run.tzinfo else "None"
            print(f"- Job '{job_id}': Next run at {next_run} (Timezone: {timezone_name})")
            
            if timezone_name != "Asia/Bangkok":
                all_correct = False
                print(f"  ❌ WARNING: Job '{job_id}' is not using Asia/Bangkok timezone!")
        
        if all_correct:
            print("✅ All jobs are correctly using Asia/Bangkok timezone.")
        
        # Add a test job to run in 5 seconds
        print("\nTESTING ACTUAL JOB EXECUTION:")
        print("Adding test job to run in 5 seconds...")
        
        # Schedule the job
        next_run = datetime.now(scheduler.timezone) + timedelta(seconds=5)
        scheduler.add_job(
            test_job,
            'date',
            run_date=next_run,
            id='timezone_test_job'
        )
        print(f"Job scheduled for: {next_run}")
        
        # Wait for job execution
        print("Waiting for job to execute...")
        start_time = time.time()
        job_executed_success = job_executed.wait(timeout=10)
        elapsed = time.time() - start_time
        
        if job_executed_success:
            # Job was executed
            global execution_time
            print(f"Job executed at: {execution_time}")
            print(f"Execution took {elapsed:.2f} seconds (expected ~5 seconds)")
            
            if 4.8 <= elapsed <= 5.5:  # Allow small variance
                print("✅ SUCCESS: Job executed at the expected time!")
            else:
                print(f"❌ WARNING: Job execution time ({elapsed:.2f}s) was not as expected (~5s)!")
        else:
            print("❌ FAILURE: Job did not execute within the timeout period!")
        
        # Cleanup - only try to remove if it exists
        try:
            scheduler.remove_job('timezone_test_job')
        except:
            pass  # Job might have been removed automatically
        
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    main()
