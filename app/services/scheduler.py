"""
Scheduler Service - APScheduler integration for Flask
Provides job scheduling capabilities for the application
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, current_app
from pytz import utc
import pytz

# Configure logger
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def init_scheduler(app: Flask) -> None:
    """
    Initialize the scheduler with the Flask application
    
    Args:
        app: The Flask application
    """
    global scheduler
    
    if scheduler:
        logger.info("Scheduler already initialized")
        return
    
    # Get configuration
    job_stores = {
        'default': SQLAlchemyJobStore(url=app.config.get('SCHEDULER_JOBSTORE_URL', 'sqlite:///app/data/jobs.sqlite'))
    }
    
    # Get timezone from app config
    timezone_str = app.config.get('SCHEDULER_TIMEZONE') or app.config.get('TIMEZONE', 'UTC')
    try:
        timezone = pytz.timezone(timezone_str)
        logger.info(f"Using timezone: {timezone}")
    except:
        logger.warning(f"Unknown timezone: {timezone_str}, falling back to UTC")
        timezone = utc
    
    # Create scheduler
    scheduler = BackgroundScheduler(
        jobstores=job_stores,
        timezone=timezone,
        job_defaults={
            'coalesce': app.config.get('SCHEDULER_COALESCE', True),
            'max_instances': app.config.get('SCHEDULER_MAX_INSTANCES', 1)
        }
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")


def get_scheduler() -> Optional[BackgroundScheduler]:
    """
    Get the current scheduler instance
    
    Returns:
        The scheduler instance or None if not initialized
    """
    global scheduler
    return scheduler


def add_interval_job(
    func: str,
    job_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    seconds: Optional[int] = None,
    minutes: Optional[int] = None,
    hours: Optional[int] = None,
    days: Optional[int] = None,
    args: Optional[List] = None,
    kwargs: Optional[Dict] = None
) -> str:
    """
    Add an interval job to the scheduler
    
    Args:
        func: Function to execute (module.function_name)
        job_id: Optional job ID (generated if not provided)
        name: Optional job name
        description: Optional job description
        seconds: Run interval in seconds
        minutes: Run interval in minutes
        hours: Run interval in hours
        days: Run interval in days
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
    
    Returns:
        The job ID
    
    Raises:
        ValueError: If no interval parameters are provided
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    # Ensure at least one interval parameter is provided
    if seconds is None and minutes is None and hours is None and days is None:
        raise ValueError("At least one interval parameter must be provided")
    
    # Import the function
    func_obj = _import_function(func)
    
    # Create trigger
    trigger = IntervalTrigger(
        seconds=seconds,
        minutes=minutes,
        hours=hours,
        days=days,
        timezone=scheduler.timezone
    )
    
    # Add job
    job = scheduler.add_job(
        func=func_obj,
        trigger=trigger,
        id=job_id,
        name=name,
        description=description,
        args=args or [],
        kwargs=kwargs or {},
        replace_existing=True
    )
    
    logger.info(f"Added interval job with ID {job.id}")
    return job.id


def add_cron_job(
    func: str,
    cron_expression: str,
    job_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    args: Optional[List] = None,
    kwargs: Optional[Dict] = None
) -> str:
    """
    Add a cron job to the scheduler
    
    Args:
        func: Function to execute (module.function_name)
        cron_expression: Cron expression (e.g. "0 0 * * *" for daily at midnight)
        job_id: Optional job ID (generated if not provided)
        name: Optional job name
        description: Optional job description
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
    
    Returns:
        The job ID
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    # Import the function
    func_obj = _import_function(func)
    
    # Parse cron expression
    cron_parts = cron_expression.split()
    if len(cron_parts) != 5:
        raise ValueError("Invalid cron expression, must have 5 parts")
    
    # Create trigger from cron expression
    trigger = CronTrigger.from_crontab(cron_expression, timezone=scheduler.timezone)
    
    # Add job
    job = scheduler.add_job(
        func=func_obj,
        trigger=trigger,
        id=job_id,
        name=name,
        description=description,
        args=args or [],
        kwargs=kwargs or {},
        replace_existing=True
    )
    
    logger.info(f"Added cron job with ID {job.id}")
    return job.id


def add_date_job(
    func: str,
    run_date: Union[str, datetime],
    job_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    args: Optional[List] = None,
    kwargs: Optional[Dict] = None
) -> str:
    """
    Add a one-time job to run at a specific date/time
    
    Args:
        func: Function to execute (module.function_name)
        run_date: Date/time to run the job (ISO format string or datetime object)
        job_id: Optional job ID (generated if not provided)
        name: Optional job name
        description: Optional job description
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
    
    Returns:
        The job ID
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    # Import the function
    func_obj = _import_function(func)
    
    # Convert string date to datetime if needed
    if isinstance(run_date, str):
        run_date = datetime.fromisoformat(run_date)
    
    # Create trigger
    trigger = DateTrigger(run_date=run_date, timezone=scheduler.timezone)
    
    # Add job
    job = scheduler.add_job(
        func=func_obj,
        trigger=trigger,
        id=job_id,
        name=name,
        description=description,
        args=args or [],
        kwargs=kwargs or {},
        replace_existing=True
    )
    
    logger.info(f"Added date job with ID {job.id} to run at {run_date}")
    return job.id


def remove_job(job_id: str) -> bool:
    """
    Remove a job from the scheduler
    
    Args:
        job_id: The job ID to remove
    
    Returns:
        True if the job was removed, False if it didn't exist
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed job with ID {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to remove job {job_id}: {str(e)}")
        return False


def pause_job(job_id: str) -> bool:
    """
    Pause a job
    
    Args:
        job_id: The job ID to pause
    
    Returns:
        True if the job was paused, False if it didn't exist
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    try:
        scheduler.pause_job(job_id)
        logger.info(f"Paused job with ID {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to pause job {job_id}: {str(e)}")
        return False


def resume_job(job_id: str) -> bool:
    """
    Resume a paused job
    
    Args:
        job_id: The job ID to resume
    
    Returns:
        True if the job was resumed, False if it didn't exist
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    try:
        scheduler.resume_job(job_id)
        logger.info(f"Resumed job with ID {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to resume job {job_id}: {str(e)}")
        return False


def run_job(job_id: str) -> bool:
    """
    Run a job immediately
    
    Args:
        job_id: The job ID to run
    
    Returns:
        True if the job was triggered, False if it didn't exist
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    try:
        scheduler.get_job(job_id).func(*scheduler.get_job(job_id).args, **scheduler.get_job(job_id).kwargs)
        logger.info(f"Triggered job with ID {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to trigger job {job_id}: {str(e)}")
        return False


def get_jobs() -> List[Dict[str, Any]]:
    """
    Get all scheduled jobs
    
    Returns:
        List of job information dictionaries
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    jobs = []
    for job in scheduler.get_jobs():
        job_type = None
        job_info = None
        
        # Determine job type and specific info
        if isinstance(job.trigger, IntervalTrigger):
            job_type = "interval"
            job_info = {
                "seconds": job.trigger.interval.total_seconds()
            }
        elif isinstance(job.trigger, CronTrigger):
            job_type = "cron"
            job_info = {
                "cron": job.trigger.expression
            }
        elif isinstance(job.trigger, DateTrigger):
            job_type = "date"
            job_info = {
                "run_date": job.trigger.run_date.isoformat()
            }
        
        # Get next run time
        next_run_time = None
        if job.next_run_time:
            next_run_time = job.next_run_time.isoformat()
        
        # Get function path
        func_path = f"{job.func.__module__}.{job.func.__name__}"
        
        # Add job info
        jobs.append({
            "id": job.id,
            "name": job.name,
            "type": job_type,
            "func": func_path,
            "args": job.args,
            "kwargs": job.kwargs,
            "description": job.description,
            "next_run_time": next_run_time,
            **job_info
        })
    
    return jobs


def setup_default_jobs() -> Tuple[bool, str, List[str]]:
    """
    Set up default monitoring jobs for the application
    
    Returns:
        Tuple of (success, message, job_ids)
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler not initialized")
    
    job_ids = []
    
    try:
        # Plants data collector (every 15 minutes)
        plants_job_id = add_interval_job(
            func="script.plants_data_collector.run",
            name="Plants Data Collector",
            description="Collects data from Growatt plants every 15 minutes",
            minutes=15
        )
        job_ids.append(plants_job_id)
        
        # Devices data collector (every 10 minutes)
        devices_job_id = add_interval_job(
            func="script.devices_data_collector.run",
            name="Devices Data Collector",
            description="Collects data from Growatt devices every 10 minutes",
            minutes=10
        )
        job_ids.append(devices_job_id)
        
        # Device status service (every 5 minutes)
        status_job_id = add_interval_job(
            func="script.device_status_service.run",
            name="Device Status Service",
            description="Updates device statuses every 5 minutes",
            minutes=5
        )
        job_ids.append(status_job_id)
        
        # Offline device notifications (every hour)
        notifications_job_id = add_interval_job(
            func="script.send_offline_device_notifications.run",
            name="Offline Device Notifications",
            description="Sends notifications for offline devices every hour",
            hours=1
        )
        job_ids.append(notifications_job_id)
        
        return True, "Default jobs set up successfully", job_ids
    
    except Exception as e:
        logger.error(f"Failed to set up default jobs: {str(e)}")
        return False, f"Failed to set up default jobs: {str(e)}", job_ids


def _import_function(func_path: str) -> callable:
    """
    Import a function from a module path string
    
    Args:
        func_path: Module path to the function (e.g. "app.services.background_service.update_status")
    
    Returns:
        The function object
    
    Raises:
        ImportError: If the function could not be imported
    """
    try:
        module_path, func_name = func_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[func_name])
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        error_msg = f"Could not import function {func_path}: {str(e)}"
        logger.error(error_msg)
        raise ImportError(error_msg) from e


def shutdown():
    """
    Shutdown the scheduler
    """
    global scheduler
    
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shutdown successfully")