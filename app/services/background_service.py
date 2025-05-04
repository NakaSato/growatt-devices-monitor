"""
Background service for device monitoring.

This module provides a background scheduler to monitor device status
at regular intervals without needing cron jobs, using APScheduler.
"""

import logging
from datetime import datetime
from functools import wraps

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logger = logging.getLogger(__name__)

class BackgroundService:
    """
    Background service for running scheduled tasks using APScheduler.
    This class serves as a singleton wrapper around the APScheduler
    to manage scheduled tasks for the Growatt Devices Monitor.
    """
    
    def __init__(self):
        """Initialize the background service."""
        self.scheduler = None
        self.initialized = False
        self.app_context = None
        self.jobs = {}
    
    def is_running(self):
        """
        Check if the background service scheduler is running.
        
        Returns:
            bool: True if the scheduler is initialized and running, False otherwise
        """
        return self.initialized and self.scheduler and self.scheduler.running
    
    def init_app(self, app: Flask):
        """
        Initialize the background service with a Flask application.
        
        Args:
            app: Flask application instance
        """
        if self.initialized:
            logger.warning("Background service already initialized")
            return
        
        # Store app for context management
        self.app = app
        
        # Get scheduler configuration from app config
        timezone = app.config.get('TIMEZONE', 'UTC')
        
        # Initialize scheduler with configuration from app.config
        jobstores = {}
        executors = {}
        job_defaults = {}
        
        # Configure jobstores if specified
        if app.config.get('USE_SQLALCHEMY_JOBSTORE', False):
            try:
                from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
                from app.database import get_db_url
                
                # Use database URL for persistent job storage
                db_url = get_db_url()
                jobstores['default'] = SQLAlchemyJobStore(url=db_url)
                logger.info("Using SQLAlchemy jobstore for persistent jobs")
            except ImportError:
                logger.warning("SQLAlchemyJobStore requested but SQLAlchemy not installed")
                # Fallback to memory jobstore
                jobstores['default'] = 'memory'
        
        # Get executors configuration
        if 'SCHEDULER_EXECUTORS' in app.config:
            executors = app.config.get('SCHEDULER_EXECUTORS', {
                'default': {'type': 'threadpool', 'max_workers': 10}
            })
        
        # Get job defaults configuration
        if 'SCHEDULER_JOB_DEFAULTS' in app.config:
            job_defaults = app.config.get('SCHEDULER_JOB_DEFAULTS', {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60
            })
        
        # Create the scheduler with our configuration
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=timezone
        )
                
        # Configure app context for jobs
        self.app_context = app.app_context
        
        # Register shutdown with Flask
        @app.teardown_appcontext
        def shutdown_scheduler(exception=None):
            self.shutdown()
        
        # Start the scheduler
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Background service initialized and scheduler started")
            
        self.initialized = True
        
        # Add monitoring jobs if enabled
        if app.config.get('ENABLE_BACKGROUND_MONITORING', True):
            self._setup_monitoring_jobs(app)
    
    def _setup_monitoring_jobs(self, app):
        """
        Set up the default monitoring jobs based on app configuration.
        
        Args:
            app: Flask application instance with configuration
        """
        # Check if we should run device status monitoring
        if app.config.get('MONITOR_DEVICE_STATUS', True):
            interval_minutes = app.config.get('DEVICE_STATUS_CHECK_INTERVAL_MINUTES', 5)
            self.add_interval_job(
                func='app.services.device_status_tracker:check_devices_status',
                id='device_status_monitor',
                minutes=interval_minutes,
                description=f"Monitor device status every {interval_minutes} minutes"
            )
            logger.info(f"Scheduled device status monitoring every {interval_minutes} minutes")
        
        # Check if we should collect device data
        if app.config.get('COLLECT_DEVICE_DATA', True):
            # Set up device data collection (default: every 15 minutes during daylight hours)
            cron_expr = app.config.get('DEVICE_DATA_CRON', '*/15 6-20 * * *')
            self.add_cron_job(
                func='app.data_collector:collect_device_data',
                id='device_data_collector',
                cron=cron_expr,
                description=f"Collect device data on schedule: {cron_expr}"
            )
            logger.info(f"Scheduled device data collection with cron: {cron_expr}")
        
        # Check if we should collect plant data
        if app.config.get('COLLECT_PLANT_DATA', True):
            # Set up plant data collection (default: every 15 minutes during daylight hours)
            cron_expr = app.config.get('PLANT_DATA_CRON', '*/15 6-20 * * *')
            self.add_cron_job(
                func='app.data_collector:collect_plant_data',
                id='plant_data_collector',
                cron=cron_expr,
                description=f"Collect plant data on schedule: {cron_expr}"
            )
            logger.info(f"Scheduled plant data collection with cron: {cron_expr}")
    
    def add_interval_job(self, func, id, **kwargs):
        """
        Add a job to run at regular intervals.
        
        Args:
            func: Function or import string to call
            id: Unique job identifier
            **kwargs: Additional arguments for IntervalTrigger
            
        Returns:
            The scheduled job
        """
        if not self.initialized or not self.scheduler:
            logger.error("Cannot add job - scheduler not initialized")
            return None
        
        # Parse function if it's a string
        if isinstance(func, str):
            func = self._import_function(func)
            if not func:
                return None
        
        # Add job with app context
        description = kwargs.pop('description', None)
        wrapped_func = self._wrap_with_app_context(func)
        
        trigger = IntervalTrigger(**kwargs)
        job = self.scheduler.add_job(
            wrapped_func,
            trigger=trigger,
            id=id,
            replace_existing=True,
            name=description or id
        )
        
        # Store in internal tracking
        self.jobs[id] = {
            'job': job,
            'description': description,
            'type': 'interval',
            'config': kwargs
        }
        
        return job
    
    def add_cron_job(self, func, id, cron, **kwargs):
        """
        Add a job to run on a cron schedule.
        
        Args:
            func: Function or import string to call
            id: Unique job identifier
            cron: Cron expression (e.g. "*/15 6-20 * * *")
            **kwargs: Additional arguments for job
            
        Returns:
            The scheduled job
        """
        if not self.initialized or not self.scheduler:
            logger.error("Cannot add job - scheduler not initialized")
            return None
        
        # Parse function if it's a string
        if isinstance(func, str):
            func = self._import_function(func)
            if not func:
                return None
        
        # Add job with app context
        description = kwargs.pop('description', None)
        wrapped_func = self._wrap_with_app_context(func)
        
        # Convert cron string to trigger if needed
        if isinstance(cron, str):
            # Parse the cron expression
            minute, hour, day, month, day_of_week = cron.split()[:5]
            trigger = CronTrigger(
                minute=minute, 
                hour=hour, 
                day=day, 
                month=month, 
                day_of_week=day_of_week
            )
        else:
            trigger = cron
        
        job = self.scheduler.add_job(
            wrapped_func,
            trigger=trigger,
            id=id,
            replace_existing=True,
            name=description or id,
            **kwargs
        )
        
        # Store in internal tracking
        self.jobs[id] = {
            'job': job,
            'description': description,
            'type': 'cron',
            'config': {'cron': cron, **kwargs}
        }
        
        return job
    
    def _import_function(self, import_path):
        """
        Import a function from a string path.
        
        Args:
            import_path: String in format 'module.submodule:function_name'
            
        Returns:
            The imported function or None if import fails
        """
        try:
            module_path, function_name = import_path.split(':')
            module = __import__(module_path, fromlist=[function_name])
            return getattr(module, function_name)
        except (ImportError, AttributeError, ValueError) as e:
            logger.error(f"Error importing function {import_path}: {e}")
            return None
    
    def _wrap_with_app_context(self, func):
        """
        Wrap a function to run within the Flask application context.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function that runs within app context
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.app_context:
                with self.app_context():
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    
    def remove_job(self, job_id):
        """
        Remove a scheduled job.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            True if job was removed, False otherwise
        """
        if not self.initialized or not self.scheduler:
            logger.error("Cannot remove job - scheduler not initialized")
            return False
        
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logger.info(f"Removed scheduled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
            return False
    
    def get_jobs(self):
        """
        Get a list of all scheduled jobs.
        
        Returns:
            List of job information dictionaries
        """
        if not self.initialized or not self.scheduler:
            logger.error("Cannot get jobs - scheduler not initialized")
            return []
        
        result = []
        
        # Get all jobs from the scheduler
        for job in self.scheduler.get_jobs():
            # Get the next run time in a readable format
            next_run = job.next_run_time
            next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else 'Not scheduled'
            
            # Get additional info from our tracking
            job_info = self.jobs.get(job.id, {})
            
            # Create the job info dict
            job_data = {
                'id': job.id,
                'name': job.name,
                'type': job_info.get('type', 'unknown'),
                'next_run': next_run_str,
                'active': job.next_run_time is not None,
                'description': job_info.get('description', ''),
                'config': job_info.get('config', {})
            }
            
            result.append(job_data)
        
        return result
    
    def pause_job(self, job_id):
        """
        Pause a scheduled job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if job was paused, False otherwise
        """
        if not self.initialized or not self.scheduler:
            logger.error("Cannot pause job - scheduler not initialized")
            return False
        
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused scheduled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id):
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if job was resumed, False otherwise
        """
        if not self.initialized or not self.scheduler:
            logger.error("Cannot resume job - scheduler not initialized")
            return False
        
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed scheduled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False
    
    def shutdown(self):
        """Shut down the scheduler."""
        if self.scheduler and self.scheduler.running:
            # Prevent shutdown from within a job context to avoid deadlocks
            import threading
            if threading.current_thread() is threading.main_thread():
                self.scheduler.shutdown()
                logger.info("Background service scheduler shutdown")
                self.initialized = False
            else:
                logger.info("Shutdown requested from a job thread - deferring to avoid deadlock")
                # Schedule the shutdown to happen from another thread
                import threading
                threading.Thread(target=self._safe_shutdown).start()
    
    def _safe_shutdown(self):
        """Safely shut down the scheduler from a separate thread."""
        try:
            if self.scheduler and self.scheduler.running:
                # Using shutdown(wait=False) to avoid waiting for jobs to complete
                self.scheduler.shutdown(wait=False)
                logger.info("Background service scheduler safely shutdown from separate thread")
                self.initialized = False
        except Exception as e:
            logger.error(f"Error during safe shutdown: {e}")

# Create a singleton instance to be imported by other modules
background_service = BackgroundService()