"""
Operations Scheduler Module

This module provides routes for managing and controlling the application's 
scheduled tasks and background services. It allows for monitoring, starting,
stopping, and configuring various scheduled jobs that handle data collection,
system maintenance, and health monitoring.
"""

import os
import logging
import datetime
import psutil
from functools import wraps
from typing import Dict, List, Optional, Union, Tuple, Any

from flask import Blueprint, jsonify, request, current_app, Response
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.base import STATE_STOPPED, STATE_RUNNING, STATE_PAUSED

from app import config
from app.database import get_db_connection
from app.services.scheduler import get_scheduler, register_jobs
from app.services.background_service import BackgroundServiceManager
from app.services.device_status_tracker import DeviceStatusTracker
from app.services.notification_service import NotificationService
from app.services.plant_service import PlantService
from app.cache_utils import clear_cache

# Create operations scheduler blueprint
operations_scheduler_bp = Blueprint('operations_scheduler', __name__, url_prefix='/api/operations/scheduler')

# Configure logging
logger = logging.getLogger(__name__)

# Decorator for admin-only access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user has admin privileges (implement your auth logic here)
        # For now, we'll just check a config flag for demo purposes
        if not current_app.config.get('ADMIN_ACCESS_ENABLED', False):
            return jsonify({
                'success': False, 
                'message': 'Administrator access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

@operations_scheduler_bp.route('/status', methods=['GET'])
def get_scheduler_status():
    """Get the current status of all scheduled jobs"""
    try:
        scheduler = get_scheduler()
        
        # Get all jobs
        jobs = []
        for job in scheduler.get_jobs():
            # Calculate next run time relative to now
            next_run = job.next_run_time
            next_run_str = 'Not scheduled' if next_run is None else next_run.strftime('%Y-%m-%d %H:%M:%S')
            
            # Format trigger info based on trigger type
            trigger_info = ''
            if hasattr(job.trigger, 'interval'):
                seconds = job.trigger.interval.total_seconds()
                if seconds < 60:
                    trigger_info = f'Every {seconds} seconds'
                elif seconds < 3600:
                    trigger_info = f'Every {seconds // 60} minutes'
                else:
                    trigger_info = f'Every {seconds // 3600} hours'
            elif hasattr(job.trigger, 'fields'):
                # This is a cron trigger
                cron_fields = []
                for field in job.trigger.fields:
                    if not field.is_default:
                        cron_fields.append(f"{field.name}={field}")
                trigger_info = 'Cron: ' + ', '.join(cron_fields)
                
            # Build job info
            job_info = {
                'id': job.id,
                'name': job.name,
                'func': job.func_ref,
                'next_run': next_run_str,
                'trigger_type': job.trigger.__class__.__name__,
                'trigger_info': trigger_info,
                'active': job.next_run_time is not None
            }
            jobs.append(job_info)
            
        # Get scheduler state
        scheduler_state = {
            'state': scheduler.state,
            'running': scheduler.state == STATE_RUNNING,
            'paused': scheduler.state == STATE_PAUSED,
            'stopped': scheduler.state == STATE_STOPPED,
            'job_count': len(jobs)
        }
            
        return jsonify({
            'success': True,
            'scheduler': scheduler_state,
            'jobs': jobs
        })
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to get scheduler status: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/pause', methods=['POST'])
@admin_required
def pause_scheduler():
    """Pause the scheduler"""
    try:
        scheduler = get_scheduler()
        scheduler.pause()
        logger.info("Scheduler paused successfully")
        return jsonify({
            'success': True,
            'message': 'Scheduler paused successfully'
        })
    except Exception as e:
        logger.error(f"Error pausing scheduler: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to pause scheduler: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/resume', methods=['POST'])
@admin_required
def resume_scheduler():
    """Resume the scheduler"""
    try:
        scheduler = get_scheduler()
        scheduler.resume()
        logger.info("Scheduler resumed successfully")
        return jsonify({
            'success': True,
            'message': 'Scheduler resumed successfully'
        })
    except Exception as e:
        logger.error(f"Error resuming scheduler: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to resume scheduler: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/job/pause', methods=['POST'])
@admin_required
def pause_job():
    """Pause a specific job"""
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({
            'success': False,
            'message': 'Job ID is required'
        }), 400
        
    try:
        scheduler = get_scheduler()
        scheduler.pause_job(job_id)
        logger.info(f"Job {job_id} paused successfully")
        return jsonify({
            'success': True,
            'message': f'Job {job_id} paused successfully'
        })
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to pause job: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/job/resume', methods=['POST'])
@admin_required
def resume_job():
    """Resume a specific job"""
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({
            'success': False,
            'message': 'Job ID is required'
        }), 400
        
    try:
        scheduler = get_scheduler()
        scheduler.resume_job(job_id)
        logger.info(f"Job {job_id} resumed successfully")
        return jsonify({
            'success': True,
            'message': f'Job {job_id} resumed successfully'
        })
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to resume job: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/job/run-now', methods=['POST'])
@admin_required
def run_job_now():
    """Run a specific job immediately"""
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({
            'success': False,
            'message': 'Job ID is required'
        }), 400
        
    try:
        scheduler = get_scheduler()
        job = scheduler.get_job(job_id)
        
        if not job:
            return jsonify({
                'success': False,
                'message': f'Job with ID {job_id} not found'
            }), 404
            
        # Run the job function directly
        job.func(*job.args, **job.kwargs)
        
        logger.info(f"Job {job_id} executed manually")
        return jsonify({
            'success': True,
            'message': f'Job {job_id} executed successfully'
        })
    except Exception as e:
        logger.error(f"Error executing job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to execute job: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/job/modify', methods=['POST'])
@admin_required
def modify_job():
    """Modify an existing job's schedule"""
    job_id = request.json.get('job_id')
    trigger_type = request.json.get('trigger_type')
    trigger_args = request.json.get('trigger_args', {})
    
    if not all([job_id, trigger_type]):
        return jsonify({
            'success': False,
            'message': 'Job ID and trigger type are required'
        }), 400
        
    try:
        scheduler = get_scheduler()
        job = scheduler.get_job(job_id)
        
        if not job:
            return jsonify({
                'success': False,
                'message': f'Job with ID {job_id} not found'
            }), 404
            
        # Create the appropriate trigger
        if trigger_type == 'interval':
            # Convert string values to integers
            for key in ['weeks', 'days', 'hours', 'minutes', 'seconds']:
                if key in trigger_args:
                    trigger_args[key] = int(trigger_args[key])
                    
            trigger = IntervalTrigger(**trigger_args)
        elif trigger_type == 'cron':
            trigger = CronTrigger(**trigger_args)
        else:
            return jsonify({
                'success': False,
                'message': f'Unsupported trigger type: {trigger_type}'
            }), 400
            
        # Reschedule the job
        scheduler.reschedule_job(job_id, trigger=trigger)
        
        logger.info(f"Job {job_id} schedule modified successfully")
        return jsonify({
            'success': True,
            'message': f'Job {job_id} schedule modified successfully'
        })
    except Exception as e:
        logger.error(f"Error modifying job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to modify job: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health metrics including CPU, memory, disk usage and services status"""
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_usage = {
            'total': f"{memory.total / (1024 ** 3):.2f} GB",
            'available': f"{memory.available / (1024 ** 3):.2f} GB",
            'used': f"{memory.used / (1024 ** 3):.2f} GB",
            'percent': memory.percent
        }
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_usage = {
            'total': f"{disk.total / (1024 ** 3):.2f} GB",
            'used': f"{disk.used / (1024 ** 3):.2f} GB",
            'free': f"{disk.free / (1024 ** 3):.2f} GB",
            'percent': disk.percent
        }
        
        # Get uptime
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        # Get service status
        background_service_manager = BackgroundServiceManager()
        services = background_service_manager.get_all_services_status()
        
        # Get database connection status
        db_status = "connected"
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
        except Exception as e:
            db_status = f"error: {str(e)}"
            
        # Determine overall system status
        status = "healthy"
        status_text = "All systems operational"
        
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = "critical"
            status_text = "System resources critically low"
        elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 75:
            status = "warning"
            status_text = "System resources under pressure"
            
        # Check service status
        service_issues = [s for s in services if s.get('status') != 'operational']
        if service_issues:
            if status != "critical":
                status = "warning"
                service_names = ", ".join([s.get('name', 'Unknown') for s in service_issues])
                status_text = f"Services with issues: {service_names}"
                
        # Database status
        if db_status != "connected":
            status = "critical"
            status_text = "Database connection error"
            
        # Build API data
        api_data = {
            'requestsPerMinute': current_app.config.get('REQUEST_RATE', 0),
            'avgResponseTime': current_app.config.get('AVG_RESPONSE_TIME', 0),
            'errorRate': current_app.config.get('ERROR_RATE', 0),
            'totalErrors': current_app.config.get('TOTAL_ERRORS', 0),
            'currentRequests': current_app.config.get('CURRENT_REQUESTS', 0),
            'endpoints': []
        }

        # Get sample endpoints for demonstration
        api_endpoints = [
            {
                'path': '/api/plants',
                'requests': 1245,
                'avgResponseTime': 42,
                'errorRate': 0.2,
                'status': 'healthy'
            },
            {
                'path': '/api/devices',
                'requests': 2156,
                'avgResponseTime': 38,
                'errorRate': 0.5,
                'status': 'healthy'
            },
            {
                'path': '/api/data/energy',
                'requests': 3520,
                'avgResponseTime': 120,
                'errorRate': 2.1,
                'status': 'degraded'
            }
        ]
        api_data['endpoints'] = api_endpoints
            
        # Construct response
        health_data = {
            'status': status,
            'statusText': status_text,
            'lastChecked': datetime.datetime.now().isoformat(),
            'uptime': uptime_str,
            'startTime': boot_time.isoformat(),
            'cpuUsage': cpu_percent,
            'cpuCores': cpu_count,
            'memoryUsage': f"{memory.used / (1024 ** 3):.2f} GB",
            'totalMemory': f"{memory.total / (1024 ** 3):.2f} GB",
            'memoryUsagePercent': memory.percent,
            'diskUsage': f"{disk.used / (1024 ** 3):.2f} GB",
            'totalDisk': f"{disk.total / (1024 ** 3):.2f} GB",
            'diskUsagePercent': disk.percent,
            'services': services,
            'database': {
                'status': db_status,
                'type': 'SQLite',
                'size': get_database_size(),
                'sizeStatus': 'good' if get_database_size_in_mb() < 100 else 'warning',
                'activeConnections': 1,
                'maxConnections': 10,
                'avgQueryTime': 15,
                'failedQueries': 0,
                'queryStatus': 'good',
                'lastBackup': get_last_backup_time(),
                'backupStatus': get_backup_status()
            },
            'api': api_data,
            'recentLogs': get_recent_logs()
        }
        
        return jsonify({
            'success': True,
            'health': health_data
        })
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to get system health: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/diagnostics', methods=['POST'])
@admin_required
def run_system_diagnostics():
    """Run system diagnostics to check for issues"""
    try:
        diagnostics_results = []
        
        # Check database connectivity
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            diagnostics_results.append({
                'component': 'Database',
                'status': 'passed',
                'message': 'Database connection successful'
            })
        except Exception as e:
            diagnostics_results.append({
                'component': 'Database',
                'status': 'failed',
                'message': f'Database connection failed: {str(e)}'
            })
            
        # Check disk space
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            diagnostics_results.append({
                'component': 'Disk',
                'status': 'warning',
                'message': f'Disk usage is critical: {disk.percent}%'
            })
        else:
            diagnostics_results.append({
                'component': 'Disk',
                'status': 'passed',
                'message': f'Disk usage is acceptable: {disk.percent}%'
            })
            
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            diagnostics_results.append({
                'component': 'Memory',
                'status': 'warning',
                'message': f'Memory usage is critical: {memory.percent}%'
            })
        else:
            diagnostics_results.append({
                'component': 'Memory',
                'status': 'passed',
                'message': f'Memory usage is acceptable: {memory.percent}%'
            })
            
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            diagnostics_results.append({
                'component': 'CPU',
                'status': 'warning',
                'message': f'CPU usage is critical: {cpu_percent}%'
            })
        else:
            diagnostics_results.append({
                'component': 'CPU',
                'status': 'passed',
                'message': f'CPU usage is acceptable: {cpu_percent}%'
            })
            
        # Check scheduler status
        scheduler = get_scheduler()
        if scheduler.state == STATE_RUNNING:
            diagnostics_results.append({
                'component': 'Scheduler',
                'status': 'passed',
                'message': 'Scheduler is running'
            })
        else:
            diagnostics_results.append({
                'component': 'Scheduler',
                'status': 'warning',
                'message': f'Scheduler is not running (state: {scheduler.state})'
            })
            
        # Check log files
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
        log_files = []
        if os.path.exists(log_dir):
            for file in os.listdir(log_dir):
                if file.endswith('.log'):
                    log_path = os.path.join(log_dir, file)
                    log_size = os.path.getsize(log_path) / (1024 * 1024)  # size in MB
                    log_files.append({
                        'name': file,
                        'size': f"{log_size:.2f} MB",
                        'modified': datetime.datetime.fromtimestamp(os.path.getmtime(log_path)).isoformat()
                    })
                    
                    if log_size > 100:  # If log file is larger than 100MB
                        diagnostics_results.append({
                            'component': 'Logs',
                            'status': 'warning',
                            'message': f'Log file {file} is large: {log_size:.2f} MB'
                        })
                        
        # Overall assessment
        warnings = len([d for d in diagnostics_results if d['status'] == 'warning'])
        failures = len([d for d in diagnostics_results if d['status'] == 'failed'])
        
        overall_status = 'passed'
        if failures > 0:
            overall_status = 'failed'
        elif warnings > 0:
            overall_status = 'warning'
        
        return jsonify({
            'success': True,
            'timestamp': datetime.datetime.now().isoformat(),
            'overall_status': overall_status,
            'warnings': warnings,
            'failures': failures,
            'results': diagnostics_results,
            'log_files': log_files
        })
    except Exception as e:
        logger.error(f"Error running system diagnostics: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to run system diagnostics: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/services/restart-all', methods=['POST'])
@admin_required
def restart_all_services():
    """Restart all background services"""
    try:
        background_service_manager = BackgroundServiceManager()
        result = background_service_manager.restart_all_services()
        
        return jsonify({
            'success': True,
            'message': 'All services restart initiated',
            'restarted': result
        })
    except Exception as e:
        logger.error(f"Error restarting all services: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to restart services: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/services/<service_id>/restart', methods=['POST'])
@admin_required
def restart_service(service_id):
    """Restart a specific service"""
    try:
        background_service_manager = BackgroundServiceManager()
        result = background_service_manager.restart_service(service_id)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Service {service_id} restarted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Service {service_id} not found or could not be restarted'
            }), 404
    except Exception as e:
        logger.error(f"Error restarting service {service_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to restart service: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/services/<service_id>/status', methods=['GET'])
def check_service_status(service_id):
    """Check the status of a specific service"""
    try:
        background_service_manager = BackgroundServiceManager()
        status = background_service_manager.get_service_status(service_id)
        
        if status:
            return jsonify(status)
        else:
            return jsonify({
                'success': False,
                'message': f'Service {service_id} not found'
            }), 404
    except Exception as e:
        logger.error(f"Error checking service status {service_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to check service status: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/database/optimize', methods=['POST'])
@admin_required
def optimize_database():
    """Optimize the database (run VACUUM)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Start time
        start_time = datetime.datetime.now()
        
        # Run VACUUM
        cursor.execute("VACUUM")
        
        # Get duration
        duration = (datetime.datetime.now() - start_time).total_seconds()
        
        cursor.close()
        conn.close()
        
        # Clear cache after optimization
        clear_cache()
        
        logger.info(f"Database optimized successfully in {duration:.2f} seconds")
        return jsonify({
            'success': True,
            'message': 'Database optimized successfully',
            'duration': f"{duration:.2f} seconds"
        })
    except Exception as e:
        logger.error(f"Error optimizing database: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to optimize database: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/database/backup', methods=['POST'])
@admin_required
def backup_database():
    """Create a backup of the database"""
    try:
        # Source database path
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'growatt_data.db')
        
        # Backup directory
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'backup', 'app', 'data')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup filename with timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'growatt_data_{timestamp}.db')
        
        # Copy the database file
        import shutil
        shutil.copy2(db_path, backup_file)
        
        # Update the last backup time
        current_app.config['LAST_DB_BACKUP'] = datetime.datetime.now().isoformat()
        
        logger.info(f"Database backup created successfully: {backup_file}")
        return jsonify({
            'success': True,
            'message': 'Database backup created successfully',
            'backupPath': backup_file,
            'timestamp': timestamp
        })
    except Exception as e:
        logger.error(f"Error backing up database: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to backup database: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/logs/cleanup', methods=['POST'])
@admin_required
def cleanup_system_logs():
    """Clean up old log files"""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
        
        if not os.path.exists(log_dir):
            return jsonify({
                'success': False,
                'message': 'Log directory not found'
            }), 404
            
        # Get retention period from request or use default (30 days)
        retention_days = request.json.get('retention_days', 30)
        retention_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        
        removed_files = []
        total_size_freed = 0
        
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                log_path = os.path.join(log_dir, file)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(log_path))
                
                # If file is older than retention period
                if mod_time < retention_date:
                    file_size = os.path.getsize(log_path)
                    os.remove(log_path)
                    removed_files.append(file)
                    total_size_freed += file_size
        
        # Convert total size to MB
        total_size_freed_mb = total_size_freed / (1024 * 1024)
        
        logger.info(f"Log cleanup completed. Removed {len(removed_files)} files, freed {total_size_freed_mb:.2f} MB")
        return jsonify({
            'success': True,
            'message': f'Log cleanup completed successfully',
            'entriesRemoved': len(removed_files),
            'sizeFreed': f"{total_size_freed_mb:.2f} MB",
            'removedFiles': removed_files
        })
    except Exception as e:
        logger.error(f"Error cleaning up logs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to clean up logs: {str(e)}"
        }), 500

@operations_scheduler_bp.route('/system/health/report', methods=['GET'])
def download_system_report():
    """Generate and download a system health report"""
    try:
        # Get system health data
        health_response = get_system_health()
        health_data = health_response.json['health'] if health_response.json['success'] else {}
        
        # Run diagnostics
        diagnostics_response = run_system_diagnostics()
        diagnostics_data = diagnostics_response.json if hasattr(diagnostics_response, 'json') else {}
        
        # Format the report as HTML
        html_content = f"""
        <html>
        <head>
            <title>System Health Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .status-healthy {{ color: green; }}
                .status-warning {{ color: orange; }}
                .status-critical {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>System Health Report</h1>
            <p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>System Status: <span class="status-{health_data.get('status', 'unknown')}">{health_data.get('statusText', 'Unknown')}</span></h2>
            
            <h3>System Resources</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Uptime</td>
                    <td>{health_data.get('uptime', 'Unknown')}</td>
                </tr>
                <tr>
                    <td>CPU Usage</td>
                    <td>{health_data.get('cpuUsage', 'Unknown')}%</td>
                </tr>
                <tr>
                    <td>Memory Usage</td>
                    <td>{health_data.get('memoryUsage', 'Unknown')} / {health_data.get('totalMemory', 'Unknown')} ({health_data.get('memoryUsagePercent', 'Unknown')}%)</td>
                </tr>
                <tr>
                    <td>Disk Usage</td>
                    <td>{health_data.get('diskUsage', 'Unknown')} / {health_data.get('totalDisk', 'Unknown')} ({health_data.get('diskUsagePercent', 'Unknown')}%)</td>
                </tr>
            </table>
            
            <h3>Services Status</h3>
            <table>
                <tr>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Uptime</th>
                </tr>
        """
        
        # Add services
        for service in health_data.get('services', []):
            html_content += f"""
                <tr>
                    <td>{service.get('name', 'Unknown')}</td>
                    <td class="status-{'healthy' if service.get('status') == 'operational' else 'warning'}">{service.get('status', 'Unknown')}</td>
                    <td>{service.get('uptime', 'Unknown')}</td>
                </tr>
            """
            
        html_content += """
            </table>
            
            <h3>Database Status</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
        """
        
        # Add database info
        db_info = health_data.get('database', {})
        html_content += f"""
                <tr>
                    <td>Status</td>
                    <td class="status-{'healthy' if db_info.get('status') == 'connected' else 'critical'}">{db_info.get('status', 'Unknown')}</td>
                </tr>
                <tr>
                    <td>Size</td>
                    <td>{db_info.get('size', 'Unknown')}</td>
                </tr>
                <tr>
                    <td>Last Backup</td>
                    <td>{db_info.get('lastBackup', 'Never')}</td>
                </tr>
                <tr>
                    <td>Active Connections</td>
                    <td>{db_info.get('activeConnections', 'Unknown')} / {db_info.get('maxConnections', 'Unknown')}</td>
                </tr>
                <tr>
                    <td>Avg Query Time</td>
                    <td>{db_info.get('avgQueryTime', 'Unknown')} ms</td>
                </tr>
            </table>
            
            <h3>Diagnostics Results</h3>
            <table>
                <tr>
                    <th>Component</th>
                    <th>Status</th>
                    <th>Message</th>
                </tr>
        """
        
        # Add diagnostics results
        for result in diagnostics_data.get('results', []):
            html_content += f"""
                <tr>
                    <td>{result.get('component', 'Unknown')}</td>
                    <td class="status-{'healthy' if result.get('status') == 'passed' else 'warning' if result.get('status') == 'warning' else 'critical'}">{result.get('status', 'Unknown')}</td>
                    <td>{result.get('message', '')}</td>
                </tr>
            """
            
        html_content += """
            </table>
            
            <h3>Recent Logs</h3>
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>Level</th>
                    <th>Source</th>
                    <th>Message</th>
                </tr>
        """
        
        # Add logs
        for log in health_data.get('recentLogs', []):
            html_content += f"""
                <tr>
                    <td>{log.get('timestamp', '')}</td>
                    <td class="status-{'critical' if log.get('level') == 'ERROR' else 'warning' if log.get('level') == 'WARNING' else 'healthy'}">{log.get('level', '')}</td>
                    <td>{log.get('source', '')}</td>
                    <td>{log.get('message', '')}</td>
                </tr>
            """
            
        html_content += """
            </table>
        </body>
        </html>
        """
        
        # Return the HTML content with appropriate headers
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"system_health_report_{timestamp}.html"
        
        response = Response(html_content, mimetype='text/html')
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        
        return response
    except Exception as e:
        logger.error(f"Error generating system report: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Failed to generate system report: {str(e)}"
        }), 500

# Helper functions

def get_database_size():
    """Get the database size as a formatted string"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'growatt_data.db')
        size_bytes = os.path.getsize(db_path)
        
        # Convert to appropriate unit
        if size_bytes < 1024 * 1024:  # Less than 1 MB
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:  # Less than 1 GB
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    except Exception as e:
        logger.error(f"Error getting database size: {str(e)}")
        return "Unknown"

def get_database_size_in_mb():
    """Get the database size in megabytes"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'growatt_data.db')
        size_bytes = os.path.getsize(db_path)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0

def get_last_backup_time():
    """Get the timestamp of the last database backup"""
    try:
        # Check if we have a stored value
        if current_app.config.get('LAST_DB_BACKUP'):
            return current_app.config.get('LAST_DB_BACKUP')
            
        # Otherwise check for backup files
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'backup', 'app', 'data')
        
        if not os.path.exists(backup_dir):
            return None
            
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('growatt_data_') and f.endswith('.db')]
        
        if not backup_files:
            return None
            
        # Get the most recent backup
        backup_files.sort(reverse=True)
        latest_backup = backup_files[0]
        
        # Parse timestamp from filename (format: growatt_data_YYYYMMDD_HHMMSS.db)
        timestamp_str = latest_backup.replace('growatt_data_', '').replace('.db', '')
        backup_time = datetime.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        
        return backup_time.isoformat()
    except Exception as e:
        logger.error(f"Error getting last backup time: {str(e)}")
        return None

def get_backup_status():
    """Determine the backup status based on last backup time"""
    try:
        last_backup = get_last_backup_time()
        
        if not last_backup:
            return "missing"
            
        # Parse the ISO timestamp
        backup_time = datetime.datetime.fromisoformat(last_backup)
        now = datetime.datetime.now()
        
        # Calculate the time difference
        diff = now - backup_time
        
        # If backup is older than 7 days
        if diff.days > 7:
            return "outdated"
        else:
            return "recent"
    except Exception as e:
        logger.error(f"Error determining backup status: {str(e)}")
        return "unknown"

def get_recent_logs(count=10):
    """Get the most recent log entries"""
    logs = []
    
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
        
        if not os.path.exists(log_dir):
            return logs
            
        # Find the most recent log file
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        
        if not log_files:
            return logs
            
        # Sort by modification time (most recent first)
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
        latest_log = os.path.join(log_dir, log_files[0])
        
        # Read the last N lines
        with open(latest_log, 'r') as f:
            lines = f.readlines()
            
        # Process the most recent lines (in reverse to get the most recent first)
        for line in reversed(lines[-100:]):  # Look at the last 100 lines
            if len(logs) >= count:
                break
                
            # Parse log line (format depends on your logging configuration)
            # This is a simple example - adjust based on your actual log format
            try:
                parts = line.strip().split(' - ')
                if len(parts) >= 3:
                    timestamp_str = parts[0]
                    level = parts[1]
                    message = ' - '.join(parts[2:])
                    
                    logs.append({
                        'timestamp': timestamp_str,
                        'level': level,
                        'source': 'application',
                        'message': message
                    })
            except Exception:
                continue
                
        # Reverse to get chronological order
        logs.reverse()
        
        return logs
    except Exception as e:
        logger.error(f"Error retrieving recent logs: {str(e)}")
        return []