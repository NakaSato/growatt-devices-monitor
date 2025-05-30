"""
Helper module to register all routes with the Flask application
"""

from flask import Flask

from app.routes.main import api_blueprint as main_routes_blueprint
from app.routes.api import api_blueprint as api_routes_blueprint
from app.routes.data import data_routes
from app.routes.prediction import prediction_routes
from app.routes.device import device_status_routes
from app.routes.operations.operations_routes import operations_routes
from app.routes.operations.scheduler_routes import scheduler_routes
from app.routes.diagnosis.routes import diagnosis_routes

def register_all_routes(app: Flask) -> None:
    """
    Register all route blueprints with the Flask application
    
    Args:
        app: The Flask application instance
    """
    # Register blueprints
    app.register_blueprint(main_routes_blueprint, name="main_routes")
    app.register_blueprint(api_routes_blueprint)
    app.register_blueprint(data_routes)
    app.register_blueprint(prediction_routes)
    app.register_blueprint(device_status_routes)
    app.register_blueprint(operations_routes)
    app.register_blueprint(scheduler_routes)
    app.register_blueprint(diagnosis_routes)
    
    app.logger.info("All route blueprints registered successfully")
