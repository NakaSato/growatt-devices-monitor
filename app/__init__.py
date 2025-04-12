from flask import Flask
from flask_caching import Cache
from flask_cors import CORS
import os
from config import Config

def create_app():
    cache_config = {
        'DEBUG': Config.DEBUG,
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    app.config.from_mapping(cache_config)
    
    # Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24)
        app.logger.warning('No SECRET_KEY set, using a random one for this session')
    
    # Initialize CORS
    CORS(app)
    
    # Initialize the cache
    cache = Cache(app)
    
    # Import and register routes
    from app.routes import api_blueprint
    app.register_blueprint(api_blueprint)

    return app