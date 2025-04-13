# Package initialization

# Import the api_blueprint from the main routes file
from app.routes.main_routes import api_blueprint

# Export the api_blueprint for app.py to use
__all__ = ['api_blueprint']
