from flask import Flask
from flask_caching import Cache
from flask_cors import CORS
import os
from config import Config

def create_app():
    """Create and configure the Flask application"""
    cache_config = {
        'DEBUG': Config.DEBUG,
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    
    app = Flask(__name__)
    
    # Configure the app
    app.config.from_object(Config)
    app.config.from_mapping(cache_config)
    app.config.from_mapping(
        SECRET_KEY='dev',  # Change this to a random string in production
        DATABASE_PATH='app/data/growatt_data.db',
    )
    
    # Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24)
        app.logger.warning('No SECRET_KEY set, using a random one for this session')
    
    # Initialize CORS
    CORS(app)
    
    # Initialize the cache
    cache = Cache(app)
    
    # Import and register routes
    try:
        from app.routes import api_blueprint
        app.register_blueprint(api_blueprint)
    except ImportError:
        pass  # Skip registration if not available

    return app

# Create the application instance that can be imported
app = create_app()