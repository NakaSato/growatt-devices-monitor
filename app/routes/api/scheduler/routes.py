from flask import Blueprint, jsonify, request, current_app
from app.services.background_service import BackgroundService
import logging
import json

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint for scheduler routes
scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/scheduler")

@scheduler_bp.route("/jobs", methods=["GET"])
def get_jobs():
    """Get all scheduled jobs"""
    try:
        background_service = BackgroundService.get_instance()
        jobs = background_service.get_jobs()
        
        # Format jobs for frontend display
        formatted_jobs = []
        for job in jobs:
            job_info = {
                "id": job.id,
                "name": job.name,
                "func": job.func_ref.__module__ + ":" + job.func_ref.__name__ if hasattr(job.func_ref, "__module__") and hasattr(job.func_ref, "__name__") else str(job.func_ref),
                "args": job.args,
                "kwargs": job.kwargs,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "description": getattr(job, "description", ""),
                "type": job.trigger.__class__.__name__.replace("Trigger", "").lower()
            }
            formatted_jobs.append(job_info)
            
        return jsonify({"jobs": formatted_jobs})
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return jsonify({"error": str(e)}), 500

@scheduler_bp.route("/interval-job", methods=["POST"])
def add_interval_job():
    """Add a new interval job to the scheduler"""
    try:
        data = request.json
        
        background_service = BackgroundService.get_instance()
        
        # Extract required parameters
        job_id = data.get("job_id")
        func = data.get("func")
        # Optional parameters
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        seconds = data.get("seconds")
        minutes = data.get("minutes")
        hours = data.get("hours")
        description = data.get("description", "")
        
        # Validate required parameters
        if not func:
            return jsonify({"message": "Function reference is required"}), 400
        
        # Validate timing parameters
        if not any([seconds, minutes, hours]):
            return jsonify({"message": "At least one time parameter (seconds, minutes, hours) is required"}), 400
        
        # Create interval parameters dict
        interval_params = {}
        if seconds is not None:
            interval_params["seconds"] = seconds
        if minutes is not None:
            interval_params["minutes"] = minutes
        if hours is not None:
            interval_params["hours"] = hours
            
        # Add the job
        job = background_service.add_interval_job(
            func=func,
            job_id=job_id,
            args=args,
            kwargs=kwargs,
            description=description,
            **interval_params
        )
        
        return jsonify({
            "message": "Interval job added successfully",
            "job_id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
        }), 201
    except Exception as e:
        logger.error(f"Error adding interval job: {e}")
        return jsonify({"message": f"Error adding interval job: {str(e)}"}), 500

@scheduler_bp.route("/cron-job", methods=["POST"])
def add_cron_job():
    """Add a new cron job to the scheduler"""
    try:
        data = request.json
        
        background_service = BackgroundService.get_instance()
        
        # Extract required parameters
        job_id = data.get("job_id")
        func = data.get("func")
        cron = data.get("cron")
        # Optional parameters
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        description = data.get("description", "")
        
        # Validate required parameters
        if not func:
            return jsonify({"message": "Function reference is required"}), 400
        if not cron:
            return jsonify({"message": "Cron expression is required"}), 400
        
        # Parse cron expression and create kwargs
        cron_parts = cron.split()
        if len(cron_parts) != 5 and len(cron_parts) != 6:
            return jsonify({"message": "Invalid cron expression. Should have 5 or 6 parts."}), 400
        
        # Add the job
        job = background_service.add_cron_job(
            func=func,
            job_id=job_id,
            args=args,
            kwargs=kwargs,
            cron_expression=cron,
            description=description
        )
        
        return jsonify({
            "message": "Cron job added successfully",
            "job_id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
        }), 201
    except Exception as e:
        logger.error(f"Error adding cron job: {e}")
        return jsonify({"message": f"Error adding cron job: {str(e)}"}), 500

@scheduler_bp.route("/date-job", methods=["POST"])
def add_date_job():
    """Add a new one-time job to the scheduler"""
    try:
        data = request.json
        
        background_service = BackgroundService.get_instance()
        
        # Extract required parameters
        job_id = data.get("job_id")
        func = data.get("func")
        run_date = data.get("run_date")
        # Optional parameters
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        description = data.get("description", "")
        
        # Validate required parameters
        if not func:
            return jsonify({"message": "Function reference is required"}), 400
        if not run_date:
            return jsonify({"message": "Run date is required"}), 400
            
        # Add the job
        job = background_service.add_date_job(
            func=func,
            job_id=job_id,
            args=args,
            kwargs=kwargs,
            run_date=run_date,
            description=description
        )
        
        return jsonify({
            "message": "One-time job added successfully",
            "job_id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
        }), 201
    except Exception as e:
        logger.error(f"Error adding one-time job: {e}")
        return jsonify({"message": f"Error adding one-time job: {str(e)}"}), 500

@scheduler_bp.route("/jobs/<job_id>", methods=["DELETE"])
def remove_job(job_id):
    """Remove a job from the scheduler"""
    try:
        background_service = BackgroundService.get_instance()
        success = background_service.remove_job(job_id)
        
        if success:
            return jsonify({"message": f"Job {job_id} removed successfully"}), 200
        else:
            return jsonify({"message": f"Job {job_id} not found"}), 404
    except Exception as e:
        logger.error(f"Error removing job: {e}")
        return jsonify({"message": f"Error removing job: {str(e)}"}), 500

@scheduler_bp.route("/jobs/<job_id>/pause", methods=["POST"])
def pause_job(job_id):
    """Pause a job in the scheduler"""
    try:
        background_service = BackgroundService.get_instance()
        success = background_service.pause_job(job_id)
        
        if success:
            return jsonify({"message": f"Job {job_id} paused successfully"}), 200
        else:
            return jsonify({"message": f"Job {job_id} not found"}), 404
    except Exception as e:
        logger.error(f"Error pausing job: {e}")
        return jsonify({"message": f"Error pausing job: {str(e)}"}), 500

@scheduler_bp.route("/jobs/<job_id>/resume", methods=["POST"])
def resume_job(job_id):
    """Resume a paused job in the scheduler"""
    try:
        background_service = BackgroundService.get_instance()
        success = background_service.resume_job(job_id)
        
        if success:
            return jsonify({"message": f"Job {job_id} resumed successfully"}), 200
        else:
            return jsonify({"message": f"Job {job_id} not found"}), 404
    except Exception as e:
        logger.error(f"Error resuming job: {e}")
        return jsonify({"message": f"Error resuming job: {str(e)}"}), 500

@scheduler_bp.route("/jobs/<job_id>/run", methods=["POST"])
def run_job(job_id):
    """Run a job immediately"""
    try:
        background_service = BackgroundService.get_instance()
        success = background_service.run_job(job_id)
        
        if success:
            return jsonify({"message": f"Job {job_id} triggered successfully"}), 200
        else:
            return jsonify({"message": f"Job {job_id} not found"}), 404
    except Exception as e:
        logger.error(f"Error running job: {e}")
        return jsonify({"message": f"Error running job: {str(e)}"}), 500

@scheduler_bp.route("/setup-jobs", methods=["POST"])
def setup_default_jobs():
    """Set up default jobs for monitoring"""
    try:
        background_service = BackgroundService.get_instance()
        
        # Define default jobs to be setup
        jobs_to_setup = [
            {
                "func": "app.data_collector:collect_devices_data",
                "job_id": "collect_devices_data",
                "trigger": "interval",
                "minutes": 15,
                "description": "Collect device data from Growatt API every 15 minutes"
            },
            {
                "func": "app.data_collector:collect_plants_data",
                "job_id": "collect_plants_data",
                "trigger": "interval",
                "hours": 1,
                "description": "Collect plant data from Growatt API every hour"
            },
            {
                "func": "app.services.device_status_tracker:check_devices_status",
                "job_id": "check_devices_status",
                "trigger": "interval",
                "minutes": 30,
                "description": "Check device status and update tracking data every 30 minutes"
            },
            {
                "func": "app.services.notification_service:NotificationService.send_device_offline_notification",
                "job_id": "send_offline_notifications",
                "trigger": "cron",
                "cron": "0 9 * * *",  # Every day at 9 AM
                "description": "Send notifications for offline devices every day at 9 AM"
            }
        ]
        
        # Add each job if it doesn't already exist
        jobs_setup = []
        for job_config in jobs_to_setup:
            try:
                # Check if job already exists
                existing_job = background_service.get_job(job_config["job_id"])
                if existing_job:
                    # Skip existing jobs
                    continue
                
                # Add job based on trigger type
                if job_config["trigger"] == "interval":
                    # Extract interval parameters
                    interval_params = {}
                    for param in ["seconds", "minutes", "hours"]:
                        if param in job_config:
                            interval_params[param] = job_config[param]
                    
                    # Add interval job
                    job = background_service.add_interval_job(
                        func=job_config["func"],
                        job_id=job_config["job_id"],
                        description=job_config["description"],
                        **interval_params
                    )
                    
                elif job_config["trigger"] == "cron":
                    # Add cron job
                    job = background_service.add_cron_job(
                        func=job_config["func"],
                        job_id=job_config["job_id"],
                        description=job_config["description"],
                        cron_expression=job_config["cron"]
                    )
                
                jobs_setup.append({
                    "job_id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                })
                
            except Exception as job_error:
                logger.error(f"Error adding job {job_config['job_id']}: {job_error}")
        
        return jsonify({
            "message": f"Default jobs setup successfully ({len(jobs_setup)} jobs created)",
            "jobs_setup": jobs_setup
        }), 200
    except Exception as e:
        logger.error(f"Error setting up default jobs: {e}")
        return jsonify({"message": f"Error setting up default jobs: {str(e)}"}), 500