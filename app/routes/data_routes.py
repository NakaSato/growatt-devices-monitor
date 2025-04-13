"""
Routes for manual data collection and database management
"""

import logging
import subprocess
import sys
from flask import Blueprint, jsonify, request, current_app
from typing import Tuple, Dict, Any

from app.data_collector import GrowattDataCollector

# Create a Blueprint for data management routes
data_routes = Blueprint('data', __name__, url_prefix='/api/data')

@data_routes.route('/collect', methods=['POST'])
def collect_data() -> Tuple[Dict[str, Any], int]:
    """
    Manually trigger data collection from the Growatt API
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with collection results and status code
    """
    try:
        # Initialize collector and run collection
        collector = GrowattDataCollector()
        result = collector.collect_and_store_all_data()
        
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
        
        # Run the setup_cron.py script
        import sys
        import os
        from pathlib import Path
        
        # Get the project root directory
        project_root = str(Path(current_app.root_path).parent)
        setup_script = os.path.join(project_root, 'setup_cron.py')
        
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
        import os
        from pathlib import Path
        
        project_root = str(Path(current_app.root_path).parent)
        setup_script = os.path.join(project_root, 'setup_cron.py')
        
        # Run the script with --list flag to get current jobs
        result = subprocess.run(
            [sys.executable, setup_script, '--list'],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "status": "success",
            "jobs": result.stdout.strip(),
            "next_sync": result.stdout.strip().split("Next run:")[-1].strip() if "Next run:" in result.stdout else None
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting sync status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
