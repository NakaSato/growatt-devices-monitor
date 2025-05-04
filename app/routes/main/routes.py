import logging
import time
from typing import Tuple, Dict, Any, Union

from flask import Blueprint, jsonify, request, Response, current_app, render_template, url_for, redirect

# Import Growatt class directly
from app.core.growatt import Growatt

# Import from the common helpers module
from app.routes.common import get_plants, initialize
from app.views.templates import (
    render_analytics, render_devices, render_index, render_error_404, render_maps, render_plants, render_weather, render_operation
)
# Import the prediction routes
from app.routes.prediction import prediction_routes
# Import the data routes
from app.routes.data import data_routes
from app.services.plant_service import PlantService

# Create a Blueprint for routes
api_blueprint = Blueprint('main_routes', __name__)

# Register the data routes blueprint
api_blueprint.register_blueprint(data_routes)
# Register the prediction routes blueprint
api_blueprint.register_blueprint(prediction_routes)

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
    Index route to render the dashboard homepage.
    
    Returns:
        str: Rendered HTML template
    """
    try:
        # Check authentication status from session
        from flask import session
        authenticated = session.get('growatt_authenticated', False)
        
        # Fetch plants data to display on the dashboard
        plants_data = get_plants() if authenticated else []
        
        # If plants_data contains an error, provide an empty list instead
        if isinstance(plants_data, list) and len(plants_data) > 0 and 'error' in plants_data[0]:
            plants_data = []
            
        # Render the dashboard template with plants data
        return render_template('dashboard.html', authenticated=authenticated, plants=plants_data)
    except Exception as e:
        current_app.logger.error(f"Error rendering dashboard page: {str(e)}")
        # Fallback to direct template rendering of index
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
def plants() -> Union[str, Tuple[str, int]]:
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

@api_blueprint.route('/plant/<int:plant_id>', methods=['GET'])
def plant_detail(plant_id: int) -> Union[str, Tuple[str, int]]:
    """
    Get detailed information for a specific plant.
    
    Args:
        plant_id (int): The ID of the plant to view
        
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        # Get the plant detail using the PlantService
        plant_service = PlantService()
        plant = plant_service.get_plant_detail(plant_id)
        
        # Check if plant exists
        if not plant:
            current_app.logger.warning(f"Plant with ID {plant_id} not found.")
            # Render the specific plant not found template instead of generic 404
            return render_template('plant_not_found.html', plant_id=plant_id), 404
        
        # Render the plant detail template
        return render_template('plant_detail.html', plant=plant)
    except Exception as e:
        current_app.logger.error(f"Error in plant_detail for plant ID {plant_id}: {str(e)}")
        return render_error_404()

@api_blueprint.route('/plants_page', methods=['GET'])
def plants_page() -> Union[str, Tuple[str, int]]:
    """
    Redirect to the plants endpoint for backward compatibility.
    
    Returns:
        redirect: Redirects to the plants endpoint
    """
    return redirect(url_for('main_routes.plants'))

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
    
@api_blueprint.route('/activities', methods=['GET'])
def activities_page() -> Union[str, Tuple[str, int]]:
    """
    Render the activities page showing system activity history.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_template('activities.html')
    except Exception as e:
        logging.error(f"Error in activities_page: {str(e)}")
        return render_error_404()
    
@api_blueprint.route('/operation', methods=['GET'])
def operation_page() -> Union[str, Tuple[str, int]]:
    """
    Render the operation page for monitoring system operations.
    
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template or error response
    """
    try:
        return render_operation()
    except Exception as e:
        logging.error(f"Error in operation_page: {str(e)}")
        return render_error_404()
