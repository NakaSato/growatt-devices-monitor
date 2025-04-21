import logging
import time
from typing import Tuple, Dict, Any, Union

from flask import Blueprint, jsonify, request, Response, current_app, render_template

# Import Growatt class directly instead of utility functions
from app.core.growatt import Growatt

from app.routes.api_helpers import get_plants, initialize
from app.views.templates import (
    render_analytics, render_devices, render_index, render_error_404, render_maps, render_plants, render_weather
)
# Import the prediction routes
from app.routes.prediction_routes import prediction_routes
# Import the data routes
from app.routes.data_routes import data_routes

# Create a Blueprint for routes
api_blueprint = Blueprint('api', __name__)

# Register the prediction routes blueprint
api_blueprint.register_blueprint(prediction_routes)
# Register the data routes blueprint
api_blueprint.register_blueprint(data_routes)

# Initialize Growatt API instance
growatt_api = Growatt()
# Initialize the api_helpers module with the Growatt API instance
initialize(growatt_api)

# Track when the last login occurred
last_login_time = 0
# Session timeout in seconds (15 minutes)
SESSION_TIMEOUT = 15 * 60

# ===== Basic Page Routes =====
@api_blueprint.route('/', methods=['GET'])
def index() -> str:
    """
    Index route to render the homepage.
    
    Returns:
        str: Rendered HTML template
    """
    try:
        return render_index()
    except Exception as e:
        current_app.logger.error(f"Error rendering index page: {str(e)}")
        # Fallback to direct template rendering
        return render_template('index.html')

@api_blueprint.errorhandler(404)
def page_not_found(e) -> Tuple[str, int]:
    """
    Handle 404 errors with a custom template.
    
    Args:
        e: The error that occurred
        
    Returns:
        tuple: Rendered error template and 404 status code
    """
    current_app.logger.warning(f"404 error: {request.path}")
    return render_error_404(), 404

# Add a global error handler for 500 errors
@api_blueprint.errorhandler(500)
def server_error(e) -> Tuple[Response, int]:
    """
    Handle 500 errors with a custom response.
    
    Args:
        e: The error that occurred
        
    Returns:
        tuple: JSON response and 500 status code
    """
    current_app.logger.error(f"500 error: {str(e)}")
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "error": str(e) if current_app.debug else None
    }), 500

# Add a health check endpoint
@api_blueprint.route('/health', methods=['GET'])
def health_check() -> Tuple[Dict[str, Any], int]:
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        Tuple[Dict[str, Any], int]: Health status and HTTP status code
    """
    try:
        # Basic health check
        status = {
            "status": "up",
            "timestamp": time.time(),
            "version": getattr(current_app, 'version', 'unknown'),
            "database": "connected"
        }
        
        # Try a simple database query to verify connection
        from app.database import DatabaseConnector
        db = DatabaseConnector()
        try:
            db.query("SELECT 1")
        except Exception as e:
            status["database"] = f"error: {str(e)}"
            return jsonify(status), 503  # Service Unavailable
        
        return jsonify(status), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "down",
            "error": str(e)
        }), 503



# ===== Page Routes =====

@api_blueprint.route('/plants', methods=['GET'])
def plants_page() -> Union[str, Tuple[str, int]]:
    """
    Get the list of plants associated with the logged-in user.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        plants_data = get_plants()
        # Check if plants_data is None or empty or contains an error
        if not plants_data:
            current_app.logger.warning("No plants found for the user.")
            return render_plants([])  # Pass empty list instead of returning 404
        
        # Handle the case where plants_data is not a list
        if not isinstance(plants_data, list):
            current_app.logger.error("Invalid data format for plants.")
            return render_plants([])  # Pass empty list
        
        # Check if error is in the first item
        if len(plants_data) > 0 and 'error' in plants_data[0]:
            error_message = plants_data[0].get('error', 'Unknown error occurred fetching plant data')
            current_app.logger.error(f"API returned error: {error_message}")
            return render_plants([])  # Pass empty list with error message
            
        return render_plants(plants_data)
    except Exception as e:
        current_app.logger.error(f"Error in plants_page: {str(e)}")
        return render_plants([])  # Pass empty list instead of returning 404

@api_blueprint.route('/devices', methods=['GET'])
def devices_page() -> Union[str, Tuple[str, int]]:
    """
    Render the devices page for a specific plant.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_devices()
    except Exception as e:
        logging.error(f"Error in devices_page: {str(e)}")
        return render_error_404()

@api_blueprint.route('/weather', methods=['GET'])
def weather_page() -> Union[str, Tuple[str, int]]:
    """
    Render the weather page for a specific plant.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_weather()
    except Exception as e:
        logging.error(f"Error in weather_page: {str(e)}")
        return render_error_404()
    
@api_blueprint.route('/maps', methods=['GET'])
def maps_page() -> Union[str, Tuple[str, int]]:
    """
    Render the weather page for a specific plant.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_maps()
    except Exception as e:
        logging.error(f"Error in weather_page: {str(e)}")
        return render_error_404()
    
@api_blueprint.route('/analytics', methods=['GET'])
def analytics_page() -> Union[str, Tuple[str, int]]:
    """
    Render the weather page for a specific plant.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_analytics()
    except Exception as e:
        logging.error(f"Error in weather_page: {str(e)}")
        return render_error_404()