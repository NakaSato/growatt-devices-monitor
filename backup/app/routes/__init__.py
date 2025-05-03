# Package initialization

# Import all blueprints from the organized route folders
from app.routes.main import main_blueprint
from app.routes.api import api_routes_blueprint
from app.routes.data import data_routes
from app.routes.prediction import prediction_routes
from app.routes.device import device_status_routes
from app.routes.operations.operations_routes import operations_routes

# Export all blueprints for app.py to use
__all__ = ['main_blueprint', 'api_routes_blueprint', 'data_routes', 'prediction_routes', 'device_status_routes', 'operations_routes']
