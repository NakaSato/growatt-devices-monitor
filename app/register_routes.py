"""
Helper module to register all routes with the Flask application
"""

from flask import Flask

from app.routes import (
    api_blueprint, 
    api_routes_blueprint, 
    data_routes, 
    prediction_routes
)

def register_all_routes(app: Flask) -> None:
    """
    Register all route blueprints with the Flask application
    
    Args:
        app: The Flask application instance
    """
    # Register the main API blueprint
    app.register_blueprint(api_blueprint)
    
    # Register the API routes blueprint
    app.register_blueprint(api_routes_blueprint)
    
    # Note: The following blueprints are already registered with api_blueprint
    # in main_routes.py, but we'll register them directly as well to ensure
    # they're available even if the structure changes
    app.register_blueprint(data_routes)
    app.register_blueprint(prediction_routes)
    
    app.logger.info("All route blueprints registered successfully")
