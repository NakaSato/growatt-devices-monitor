"""
Scheduler API routes for managing background jobs.

This module provides REST API endpoints for interacting with the APScheduler
background service to manage scheduled jobs in the application.
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from http import HTTPStatus

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
scheduler_routes = Blueprint('scheduler_routes', __name__, url_prefix='/api/scheduler')

@scheduler_routes.route('/status', methods=['GET'])
def get_scheduler_status():
    """
    Get the current status of the APScheduler service along with jobs information.
    
    Returns:
        JSON response with scheduler status, job count, and jobs list
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Check if scheduler is running
        is_running = background_service.is_running()
        
        # Get all jobs
        jobs = background_service.get_jobs()
        
        # Get current server time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'status': 'running' if is_running else 'stopped',
            'server_time': current_time,
            'jobs_count': len(jobs),
            'jobs': jobs
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to get scheduler status: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/jobs', methods=['GET'])
def get_jobs():
    """
    Get all scheduled jobs.
    
    Returns:
        JSON response with list of jobs
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Get all jobs
        jobs = background_service.get_jobs()
        
        return jsonify({
            'status': 'success',
            'jobs': jobs
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to get jobs: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/jobs', methods=['POST'])
def add_job():
    """
    Add a new scheduled job.
    
    Expected JSON payload:
    {
        "type": "interval"|"cron"|"one_time",
        "id": "unique_job_id",
        "description": "Job description",
        "func": "module.path:function_name",
        "trigger_args": {
            // For interval jobs:
            "seconds": 30, or "minutes": 5, or "hours": 1, etc.
            
            // For cron jobs:
            "cron": "*/15 * * * *"
            
            // For one_time jobs:
            "run_date": "2023-01-01T12:00:00Z"
        }
    }
    
    Returns:
        JSON response with job details
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ['type', 'id', 'func']):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: type, id, func'
            }), HTTPStatus.BAD_REQUEST
        
        # Get job details
        job_type = data['type']
        job_id = data['id']
        job_func = data['func']
        job_description = data.get('description', '')
        trigger_args = data.get('trigger_args', {})
        
        # Get background service from app
        background_service = current_app.background_service
        
        # Check if job already exists
        existing_jobs = background_service.get_jobs()
        if any(job['id'] == job_id for job in existing_jobs):
            return jsonify({
                'status': 'error',
                'message': f"Job with ID '{job_id}' already exists"
            }), HTTPStatus.CONFLICT
        
        # Add job based on type
        if job_type == 'interval':
            # For interval jobs
            job = background_service.add_interval_job(
                func=job_func,
                id=job_id,
                description=job_description,
                **trigger_args
            )
        elif job_type == 'cron':
            # For cron jobs
            if 'cron' not in trigger_args:
                return jsonify({
                    'status': 'error',
                    'message': "Missing 'cron' in trigger_args for cron job"
                }), HTTPStatus.BAD_REQUEST
            
            job = background_service.add_cron_job(
                func=job_func,
                id=job_id,
                cron=trigger_args['cron'],
                description=job_description
            )
        elif job_type == 'one_time':
            # For one-time jobs
            if 'run_date' not in trigger_args:
                return jsonify({
                    'status': 'error',
                    'message': "Missing 'run_date' in trigger_args for one_time job"
                }), HTTPStatus.BAD_REQUEST
            
            job = background_service.add_one_time_job(
                func=job_func,
                id=job_id,
                run_date=trigger_args['run_date'],
                description=job_description
            )
        else:
            return jsonify({
                'status': 'error',
                'message': f"Invalid job type: {job_type}"
            }), HTTPStatus.BAD_REQUEST
        
        if not job:
            return jsonify({
                'status': 'error',
                'message': 'Failed to add job'
            }), HTTPStatus.INTERNAL_SERVER_ERROR
        
        # Return success response with job details
        return jsonify({
            'status': 'success',
            'message': f"Job '{job_id}' added successfully",
            'job_id': job_id
        }), HTTPStatus.CREATED
    except Exception as e:
        logger.error(f"Failed to add job: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to add job: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """
    Delete a scheduled job.
    
    Args:
        job_id: ID of the job to delete
    
    Returns:
        JSON response with deletion status
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Delete the job
        success = background_service.remove_job(job_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': f"Job with ID '{job_id}' not found or could not be deleted"
            }), HTTPStatus.NOT_FOUND
        
        return jsonify({
            'status': 'success',
            'message': f"Job '{job_id}' deleted successfully"
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to delete job: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/jobs/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """
    Pause a scheduled job.
    
    Args:
        job_id: ID of the job to pause
    
    Returns:
        JSON response with pause status
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Pause the job
        success = background_service.pause_job(job_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': f"Job with ID '{job_id}' not found or could not be paused"
            }), HTTPStatus.NOT_FOUND
        
        return jsonify({
            'status': 'success',
            'message': f"Job '{job_id}' paused successfully"
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to pause job: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to pause job: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/jobs/<job_id>/resume', methods=['POST'])
def resume_job(job_id):
    """
    Resume a paused job.
    
    Args:
        job_id: ID of the job to resume
    
    Returns:
        JSON response with resume status
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Resume the job
        success = background_service.resume_job(job_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': f"Job with ID '{job_id}' not found or could not be resumed"
            }), HTTPStatus.NOT_FOUND
        
        return jsonify({
            'status': 'success',
            'message': f"Job '{job_id}' resumed successfully"
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to resume job: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to resume job: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/run-now/<job_id>', methods=['POST'])
def run_job_now(job_id):
    """
    Run a scheduled job immediately (one-time execution).
    
    Args:
        job_id: ID of the job to run
    
    Returns:
        JSON response with execution status
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Get all jobs to find the one to run
        jobs = background_service.get_jobs()
        
        # Find the job
        job_info = next((job for job in jobs if job['id'] == job_id), None)
        
        if not job_info:
            return jsonify({
                'status': 'error',
                'message': f"Job with ID '{job_id}' not found"
            }), HTTPStatus.NOT_FOUND
        
        # Get the function path from job_info 
        function_path = None
        for job in jobs:
            if job['id'] == job_id:
                # Extract function info from job data
                # This might need adjustment based on how your job info is stored
                function_path = job.get('config', {}).get('function_path')
                break
        
        if not function_path:
            # If function path is not available, we'll need to get job details
            # from the scheduler itself
            logger.warning(f"Function path not found for job {job_id}, adding a one-time execution")
            
            # Add a one-time execution of the job right now
            result = background_service.add_one_time_job(
                func=f"app.services.background_service:execute_job_{job_id}",
                run_date=datetime.now(),
                id=f"run_now_{job_id}_{datetime.now().timestamp()}",
                description=f"On-demand execution of {job_id}"
            )
            
            if not result:
                return jsonify({
                    'status': 'error',
                    'message': f"Failed to schedule on-demand execution of job '{job_id}'"
                }), HTTPStatus.INTERNAL_SERVER_ERROR
        
        return jsonify({
            'status': 'success',
            'message': f"Job '{job_id}' scheduled for immediate execution"
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to run job now: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to run job: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@scheduler_routes.route('/setup-jobs', methods=['POST'])
def setup_monitoring_jobs():
    """
    Set up default monitoring jobs based on configuration.
    This is useful when starting the application without cron jobs.
    
    Returns:
        JSON response with setup status
    """
    try:
        # Get background service from app
        background_service = current_app.background_service
        
        # Get configuration from app
        config = current_app.config
        jobs_setup = []
        
        # Setup device status monitoring job
        if config.get('MONITOR_DEVICE_STATUS', True):
            interval_minutes = config.get('DEVICE_STATUS_CHECK_INTERVAL_MINUTES', 5)
            job = background_service.add_interval_job(
                func='app.services.device_status_tracker:check_devices_status',
                id='device_status_monitor',
                minutes=interval_minutes,
                description=f"Monitor device status every {interval_minutes} minutes"
            )
            if job:
                jobs_setup.append('device_status_monitor')
        
        # Setup device data collection job
        if config.get('COLLECT_DEVICE_DATA', True):
            cron_expr = config.get('DEVICE_DATA_CRON', '*/15 6-20 * * *')
            job = background_service.add_cron_job(
                func='app.data_collector:collect_devices_data',
                id='device_data_collector',
                cron=cron_expr,
                description=f"Collect device data on schedule: {cron_expr}"
            )
            if job:
                jobs_setup.append('device_data_collector')
        
        # Setup plant data collection job
        if config.get('COLLECT_PLANT_DATA', True):
            cron_expr = config.get('PLANT_DATA_CRON', '*/15 6-20 * * *')
            job = background_service.add_cron_job(
                func='app.data_collector:collect_plants_data',
                id='plant_data_collector',
                cron=cron_expr,
                description=f"Collect plant data on schedule: {cron_expr}"
            )
            if job:
                jobs_setup.append('plant_data_collector')
        
        # Setup device offline notifications job
        if config.get('SEND_OFFLINE_NOTIFICATIONS', True):
            cron_expr = config.get('OFFLINE_NOTIFICATIONS_CRON', '0 9,17 * * *')
            job = background_service.add_cron_job(
                func='app.services.notification_service:send_offline_device_notifications',
                id='offline_notifications',
                cron=cron_expr,
                description=f"Send offline device notifications on schedule: {cron_expr}"
            )
            if job:
                jobs_setup.append('offline_notifications')
        
        return jsonify({
            'status': 'success',
            'message': f"Successfully set up {len(jobs_setup)} monitoring jobs",
            'jobs_setup': jobs_setup
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Failed to set up monitoring jobs: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to set up monitoring jobs: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR