#!/usr/bin/env python3
"""
Test Postgres Scheduler

This script demonstrates setting up a scheduled job that collects data
and stores it in a PostgreSQL database using the BackgroundService scheduler.
"""

import os
import sys
import time
import logging
import random
import datetime
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("postgres-scheduler")

# Load environment variables from .env file
load_dotenv()

# Import app modules
from app.services.background_service import BackgroundService
from app.database import DatabaseConnector, get_db_connection

# For test compatibility, define a placeholder for any missing jobs
# This helps prevent errors when restoring jobs from the jobstore
def test_job():
    """
    Placeholder function for any old 'test_job' references in the jobstore.
    This prevents errors when restoring jobs from a previous run.
    """
    logger.warning("Deprecated test_job was called. This job should be removed.")
    return False

# Create a sample data collector function
def collect_solar_data():
    try:
        # Generate test data
        current_time = datetime.datetime.now().isoformat()
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Get database connector
        db = DatabaseConnector()
        
        # Generate plant data
        plant_data = [
            {
                "id": "plant001",
                "name": "Test Plant 1",
                "status": "normal",
                "created_at": current_time
            },
            {
                "id": "plant002",
                "name": "Test Plant 2",
                "status": "normal",
                "created_at": current_time
            }
        ]
        
        # Save plant data to database
        logger.info(f"Saving {len(plant_data)} plants to database")
        db.save_plant_data(plant_data)
        
        # Generate device data
        device_data = [
            {
                "serial_number": "SN001",
                "plant_id": "plant001",
                "alias": "Inverter 1",
                "type": "inverter",
                "status": "online",
                "last_updated": current_time,
                "power": random.uniform(2.5, 5.0),
                "energy_today": random.uniform(15.0, 25.0),
                "temperature": random.uniform(35.0, 45.0)
            },
            {
                "serial_number": "SN002",
                "plant_id": "plant002",
                "alias": "Inverter 2",
                "type": "inverter",
                "status": "online",
                "last_updated": current_time,
                "power": random.uniform(3.0, 6.0),
                "energy_today": random.uniform(18.0, 28.0),
                "temperature": random.uniform(36.0, 46.0)
            }
        ]
        
        logger.info(f"Saving {len(device_data)} devices to database")
        
        # Create a function to save devices without raw_data field
        def save_devices_no_raw_data(devices):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        for device in devices:
                            cursor.execute(
                                """
                                INSERT INTO devices
                                (serial_number, plant_id, alias, type, status, last_updated)
                                VALUES (%s, %s, %s, %s, %s, NOW())
                                ON CONFLICT (serial_number) DO UPDATE
                                SET plant_id = %s, alias = %s, type = %s, status = %s, last_updated = NOW()
                                """,
                                (
                                    device["serial_number"],
                                    device["plant_id"],
                                    device.get("alias", ""),
                                    device.get("type", "unknown"),
                                    device.get("status", "unknown"),
                                    device["plant_id"],
                                    device.get("alias", ""),
                                    device.get("type", "unknown"),
                                    device.get("status", "unknown")
                                )
                            )
                    conn.commit()
                logger.info(f"Successfully saved {len(devices)} devices to database")
                return True
            except Exception as e:
                logger.error(f"Unexpected error saving devices: {e}")
                return False
        
        # Save devices using our custom function that doesn't use raw_data
        save_devices_no_raw_data(device_data)
        
        # Generate energy data
        energy_data = []
        for device in device_data:
            energy_data.append({
                "plant_id": device["plant_id"],
                "mix_sn": device["serial_number"],
                "date": date_str,
                "daily_energy": device["energy_today"],
                "peak_power": device["power"] * 1.2  # Simulated peak power
            })
        
        # Save energy data to database
        count = db.save_energy_data_batch(energy_data)
        logger.info(f"Saved {count} energy records to database")
        
        # Add a weather record for each plant
        for plant in plant_data:
            weather_saved = db.save_weather_data(
                plant_id=plant["id"],
                date=date_str,
                temperature=random.uniform(20.0, 30.0),
                condition=random.choice(["Sunny", "Partly Cloudy", "Cloudy"])
            )
            if weather_saved:
                logger.info(f"Saved weather data for plant {plant['id']}")
            else:
                logger.warning(f"Failed to save weather data for plant {plant['id']}")
        
        logger.info("Data collection task completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in data collection task: {e}")
        return False

def setup_and_run_scheduler():
    """Set up the scheduler and run the data collection job."""
    logger.info("Setting up background service scheduler")
    
    # Get the singleton instance of the BackgroundService
    scheduler = BackgroundService()
    
    # Initialize the scheduler with custom configuration
    scheduler.scheduler = scheduler.scheduler or BackgroundService().scheduler
    
    if not scheduler.initialized:
        # Configure jobstores
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        from apscheduler.jobstores.base import JobLookupError
        
        # Create a custom SQLAlchemyJobStore that handles missing jobs
        class SafeSQLAlchemyJobStore(SQLAlchemyJobStore):
            def _select_jobs(self, *conditions):
                """Copy of the parent class's _select_jobs method to resolve
                the missing method error."""
                selectable = self.jobs_t.select().order_by(self.jobs_t.c.next_run_time)
                for condition in conditions:
                    selectable = selectable.where(condition)
                return self.engine.connect().execute(selectable).fetchall()
                
            def get_all_jobs(self):
                jobs = []
                failed_job_ids = []
                try:
                    # In APScheduler, job_state is the column we need to check
                    for row in self._select_jobs(self.jobs_t.c.job_state != None):
                        try:
                            # Ensure we're dealing with bytes for deserialization
                            job_state = row.job_state
                            if not isinstance(job_state, bytes):
                                logger.warning(f"Job state for {row.id} is not in bytes format. Skipping.")
                                failed_job_ids.append(row.id)
                                continue
                            
                            jobs.append(self._reconstitute_job(job_state))
                        except (KeyError, ImportError, LookupError, TypeError) as e:
                            failed_job_ids.append(row.id)
                            logger.warning(f"Could not restore job {row.id}: {e}. Will remove it.")
                except Exception as e:
                    logger.error(f"Error fetching jobs: {e}")
                
                # Remove failed jobs from jobstore
                if failed_job_ids:
                    logger.info(f"Cleaning up {len(failed_job_ids)} broken jobs from jobstore")
                    for job_id in failed_job_ids:
                        try:
                            self.remove_job(job_id)
                            logger.info(f"Removed broken job {job_id}")
                        except JobLookupError:
                            logger.warning(f"Failed to remove job {job_id} - already gone")
                
                return jobs
        
        # Use SQLite for job persistence in this test with our custom jobstore
        jobstore_url = os.getenv("SCHEDULER_JOBSTORE_URL", "sqlite:///test_jobs.sqlite")
        jobstores = {'default': SafeSQLAlchemyJobStore(url=jobstore_url)}
        
        # Configure executors
        executors = {
            'default': {'type': 'threadpool', 'max_workers': 5}
        }
        
        # Configure job defaults
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 60  # 1 minute grace time for misfires
        }
        
        # Start the scheduler
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        scheduler.scheduler.start()
        scheduler.initialized = True
        logger.info("Scheduler initialized and started")
    
    # Add the data collection job
    # Using a reference to the function since we're in the same module
    job = scheduler.add_interval_job(
        func=collect_solar_data,
        id='postgres_data_collector',
        seconds=30,  # Run every 30 seconds for testing
        description="Collect solar data and store in PostgreSQL"
    )
    
    if job:
        logger.info(f"Added job: {job.id}")
        logger.info(f"Next run time: {job.next_run_time}")
    else:
        logger.error("Failed to add job")
        return False
    
    # Get all jobs
    jobs = scheduler.get_jobs()
    logger.info(f"Scheduled jobs ({len(jobs)}):")
    for job_info in jobs:
        logger.info(f"  - {job_info['id']}: Next run at {job_info['next_run']}")
    
    return True

def main():
    """Main function to run the PostgreSQL scheduler test."""
    logger.info("Starting PostgreSQL scheduler test")
    
    # Check PostgreSQL environment variables
    required_vars = [
        "POSTGRES_HOST", 
        "POSTGRES_PORT", 
        "POSTGRES_USER", 
        "POSTGRES_PASSWORD", 
        "POSTGRES_DB"
    ]
    
    # Verify environment variables
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file")
        return 1
    
    # Set up and start the scheduler
    if not setup_and_run_scheduler():
        logger.error("Failed to set up scheduler")
        return 1
    
    # Keep the script running to allow the scheduler to execute jobs
    try:
        logger.info("Scheduler is running. Press Ctrl+C to exit.")
        
        # Run for a maximum of 5 minutes or until interrupted
        max_runtime = 300  # 5 minutes in seconds
        start_time = time.time()
        
        while True:
            time.sleep(1)
            
            # Exit after max runtime
            if time.time() - start_time > max_runtime:
                logger.info(f"Maximum runtime of {max_runtime} seconds reached. Exiting.")
                break
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down.")
    finally:
        # Shut down the scheduler gracefully
        scheduler = BackgroundService()
        if scheduler.initialized:
            logger.info("Shutting down scheduler")
            scheduler.shutdown()
    
    logger.info("Test complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())