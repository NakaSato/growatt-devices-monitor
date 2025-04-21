from typing import Tuple, List, Dict, Any, Union
from flask import render_template
import logging

# Create a logger for this module
logger = logging.getLogger(__name__)

def render_index() -> str:
    """
    Render the index template.
    
    Returns:
        str: Rendered HTML template for the index page
    """
    return render_template('index.html')

def render_plants(plants: List[Dict[str, Any]]) -> str:
    """
    Render the plants template with data.
    
    Args:
        plants (List[Dict[str, Any]]): List of plant data dictionaries
        
    Returns:
        str: Rendered HTML template for the plants page
    """
    return render_template('plants.html', plants=plants)

def render_devices(plant_id: str = '', plant_name: str = '', error: str = '') -> Union[str, Tuple[str, int]]:
    """
    Render the devices template.
    
    Args:
        plant_id (str, optional): ID of the plant to display devices for. Defaults to ''.
        plant_name (str, optional): Name of the plant to display. Defaults to ''.
        error (str, optional): Error message if devices not found. Defaults to ''.
        
    Returns:
        Union[str, Tuple[str, int]]: Rendered HTML template for the devices page or error with status code
    """
    if error:
        return render_template('error.html', 
                                    error=error,
                                    error_code="404", 
                                    error_title="Not Found"), 404
    return render_template('devices.html', plant_id=plant_id, plant_name=plant_name)

def render_device_not_found(plant_id: str = '', plant_name: str = '') -> Tuple[str, int]:
    """
    Render the devices template with not found error.
    
    Args:
        plant_id (str, optional): ID of the plant where devices weren't found. Defaults to ''.
        plant_name (str, optional): Name of the plant to display. Defaults to ''.
        
    Returns:
        Tuple[str, int]: Rendered HTML template with error message and 404 status code
    """
    error_message = f"No devices found for plant {plant_name}" if plant_name else "Device not found"
    return render_template('error.html', 
                                error=error_message,
                                error_code="404", 
                                error_title="Not Found"), 404

def render_weather(plant_id: str = '', plant_name: str = '') -> str:
    """
    Render the weather template.
    
    Args:
        plant_id (str, optional): ID of the plant to display weather for. Defaults to ''.
        plant_name (str, optional): Name of the plant to display. Defaults to ''.
        
    Returns:
        str: Rendered HTML template for the weather page
    """
    return render_template('weather.html', plant_id=plant_id, plant_name=plant_name)

def render_maps() -> Tuple[str, int]:
    """
    Render the 404 error template.
    
    Returns:
        Tuple[str, int]: Rendered HTML template for the 404 page and status code
    """
    return render_template('maps.html', 
                               error="The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
                               error_code="404", 
                               error_title="Not Found"), 404

def render_analytics() -> Tuple[str, int]:
    """
    Render the 404 error template.
    
    Returns:
        Tuple[str, int]: Rendered HTML template for the 404 page and status code
    """
    return render_template('analytics.html', 
                               error="The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
                               error_code="404", 
                               error_title="Not Found"), 404

def render_error_404() -> Tuple[str, int]:
    """
    Render the 404 error template.
    
    Returns:
        Tuple[str, int]: Rendered HTML template for the 404 page and status code
    """
    return render_template('error.html', 
                               error="The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
                               error_code="404", 
                               error_title="Not Found"), 404


