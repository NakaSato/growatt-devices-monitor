# Package initialization

# Import all blueprints from the route files
from app.routes.main_routes import api_blueprint as main_blueprint
from app.routes.api_routes import api_blueprint as api_routes_blueprint
from app.routes.data_routes import data_routes
from app.routes.prediction_routes import prediction_routes

# Export all blueprints for app.py to use
__all__ = ['main_blueprint', 'api_routes_blueprint', 'data_routes', 'prediction_routes']
