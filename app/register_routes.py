"""
Helper module to register all routes with the Flask application
"""

from flask import Flask

from app.routes.main_routes import api_blueprint as main_routes_blueprint
from app.routes.api_routes import api_blueprint as api_routes_blueprint
from app.routes.data_routes import data_routes
from app.routes.prediction_routes import prediction_routes

def register_all_routes(app: Flask) -> None:
    """
    Register all route blueprints with the Flask application
    
    Args:
        app: The Flask application instance
    """
    # Register the main routes blueprint
    app.register_blueprint(main_routes_blueprint, name="main_routes")
    
    # Register the API routes blueprint
    app.register_blueprint(api_routes_blueprint)
    
    # Register data and prediction routes
    # (These are already registered with the main blueprint in main_routes.py)
    # But we're registering them directly to ensure they're available
    app.register_blueprint(data_routes)
    app.register_blueprint(prediction_routes)
    
    app.logger.info("All route blueprints registered successfully")
