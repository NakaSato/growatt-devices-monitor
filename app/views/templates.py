from typing import Tuple, List, Dict, Any, Union
from flask import render_template

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

def render_devices(plant_name: str = '') -> str:
    """
    Render the devices template.
    
    Args:
        plant_name (str, optional): Name of the plant to display. Defaults to ''.
        
    Returns:
        str: Rendered HTML template for the devices page
    """
    return render_template('devices.html', plant_name=plant_name)

def render_weather() -> str:
    """
    Render the weather template.
    
    Returns:
        str: Rendered HTML template for the weather page
    """
    return render_template('weather.html')

def render_error_404() -> Tuple[str, int]:
    """
    Render the 404 error template.
    
    Returns:
        Tuple[str, int]: Rendered HTML template for the 404 page and status code
    """
    return render_template('404.html'), 404
