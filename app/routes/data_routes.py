"""
Routes for manual data collection and database management
"""

import logging
import subprocess
import sys
import os
from pathlib import Path
from flask import Blueprint, jsonify, request, current_app
from typing import Tuple, Dict, Any, List, Optional, Union

from app.data_collector import GrowattDataCollector
from app.database import DatabaseConnector

# Create a Blueprint for data management routes
data_routes = Blueprint('data', __name__, url_prefix='/api/data')

# Initialize the database connector
db_connector = DatabaseConnector()

# Add a simple health check route
@data_routes.route('/health', methods=['GET'])
def data_health() -> Tuple[Dict[str, Any], int]:
    """
    Health check endpoint for the data routes.
    
    Returns:
        Tuple[Dict[str, Any], int]: Health status and HTTP status code
    """
    try:
        # Check database connection
        db_connector.query("SELECT 1")
        return jsonify({
            "status": "ok",
            "message": "Data routes operational"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Data health check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Database error: {str(e)}"
        }), 500

@data_routes.route('/collect', methods=['POST'])
def collect_data() -> Tuple[Dict[str, Any], int]:
    """
    Manually trigger data collection from the Growatt API
    
    Request body (optional):
        {
            "days_back": 7,  # Number of days of historical data to collect
            "include_weather": true  # Whether to collect weather data
        }
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with collection results and status code
    """
    try:
        # Get optional parameters from request
        params = request.get_json() or {}
        days_back = params.get('days_back', 7)
        include_weather = params.get('include_weather', True)
        
        # Validate parameters
        if not isinstance(days_back, int) or days_back < 1 or days_back > 30:
            return jsonify({
                "status": "error",
                "message": "days_back must be an integer between 1 and 30"
            }), 400
        
        # Initialize collector and run collection
        collector = GrowattDataCollector()
        result = collector.collect_and_store_all_data(days_back=days_back, include_weather=include_weather)
        
        if result.get('success'):
            return jsonify({
                "status": "success",
                "message": "Data collection completed successfully",
                "stats": result.get('results', {})
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Data collection failed: {result.get('message')}",
                "partial_results": result.get('partial_results', {})
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error in collect_data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@data_routes.route('/sync/schedule', methods=['POST'])
def schedule_sync() -> Tuple[Dict[str, Any], int]:
    """
    Schedule a new cron job for data synchronization
    
    Request body should contain:
    {
        "interval": "hourly" | "daily" | "every6h" | "every12h"
    }
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with status code
    """
    try:
        # Get parameters from request
        params = request.get_json() or {}
        interval = params.get('interval', 'hourly')
        
        # Validate interval parameter
        valid_intervals = ['hourly', 'daily', 'every6h', 'every12h']
        if interval not in valid_intervals:
            return jsonify({
                "status": "error",
                "message": f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
            }), 400
        
        # Get the project root directory
        project_root = str(Path(current_app.root_path).parent)
        setup_script = os.path.join(project_root, 'setup_cron.py')
        
        # Check if script exists
        if not os.path.exists(setup_script):
            return jsonify({
                "status": "error",
                "message": f"Script not found: {setup_script}"
            }), 500
        
        # Run the script with the specified interval
        result = subprocess.run(
            [sys.executable, setup_script, '--interval', interval],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return jsonify({
                "status": "success",
                "message": f"Scheduled {interval} synchronization job",
                "details": result.stdout.strip()
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to schedule synchronization job",
                "details": result.stderr.strip()
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error scheduling sync: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@data_routes.route('/sync/status', methods=['GET'])
def sync_status() -> Tuple[Dict[str, Any], int]:
    """
    Get the status of scheduled sync jobs
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with status code
    """
    try:
        # Get the project root directory
        project_root = str(Path(current_app.root_path).parent)
        setup_script = os.path.join(project_root, 'setup_cron.py')
        
        # Check if script exists
        if not os.path.exists(setup_script):
            return jsonify({
                "status": "error",
                "message": f"Script not found: {setup_script}"
            }), 500
        
        # Run the script with --list flag to get current jobs
        result = subprocess.run(
            [sys.executable, setup_script, '--list'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": "Failed to get sync status",
                "details": result.stderr.strip()
            }), 500
        
        # Parse next run time if available
        next_run = None
        if "Next run:" in result.stdout:
            next_run = result.stdout.strip().split("Next run:")[-1].strip()
        
        return jsonify({
            "status": "success",
            "jobs": result.stdout.strip(),
            "next_sync": next_run,
            "active": "No active jobs found" not in result.stdout
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting sync status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@data_routes.route('/stats', methods=['GET'])
def get_data_stats() -> Tuple[Dict[str, Any], int]:
    """
    Get statistics about collected data in the database
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with database statistics
    """
    try:
        # Get count of records in each table
        stats = {
            "plants": len(db_connector.query("SELECT id FROM plants")),
            "devices": len(db_connector.query("SELECT sn FROM devices")),
            "energy_records": len(db_connector.query("SELECT id FROM energy_stats")),
            "weather_records": len(db_connector.query("SELECT id FROM weather")),
            "predictions": len(db_connector.query("SELECT id FROM predictions"))
        }
        
        # Get date range of data
        energy_dates = db_connector.query("""
            SELECT MIN(date) as oldest, MAX(date) as newest 
            FROM energy_stats
        """)
        
        if energy_dates and energy_dates[0]['oldest']:
            stats["oldest_data"] = energy_dates[0]['oldest']
            stats["newest_data"] = energy_dates[0]['newest']
        
        # Get database file size
        db_path = db_connector.db_path
        if os.path.exists(db_path):
            stats["database_size_bytes"] = os.path.getsize(db_path)
            stats["database_size_mb"] = round(stats["database_size_bytes"] / (1024 * 1024), 2)
        
        return jsonify({
            "status": "success",
            "statistics": stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting data statistics: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
