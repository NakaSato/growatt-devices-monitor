from flask import Flask, jsonify
from flask_caching import Cache
from flask_cors import CORS
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from app.config import Config
from app.database import init_db

# Define version
__version__ = "1.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Create and configure the Flask application
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Flask: Configured Flask application
    """
    # Define cache configuration
    cache_config = {
        'DEBUG': Config.DEBUG,
        'CACHE_TYPE': 'SimpleCache',  # Use SimpleCache instead of deprecated 'simple'
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    
    # Create Flask app
    app = Flask(__name__)
    app.url_map.strict_slashes = False  # Allow URLs with or without trailing slashes
    
    # Set version
    app.version = __version__
    
    # Load configuration from Config class
    app.config.from_object(Config)
    
    # Apply additional configuration if provided
    if config:
        app.config.from_mapping(config)
    
    # Configure the app with cache settings
    app.config.from_mapping(cache_config)
    
    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Ensure data directory exists
    data_dir = Path(app.root_path) / 'data'
    os.makedirs(data_dir, exist_ok=True)
    
    # Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24)
        logger.warning('No SECRET_KEY set, using a random one for this session')
    
    # Initialize CORS with more secure defaults
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize the cache
    cache = Cache(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Initialize database
    with app.app_context():
        init_db()
    
    # Import and register routes
    from app.routes import main_blueprint, api_routes_blueprint, data_routes, prediction_routes
    
    # Register all blueprints
    app.register_blueprint(main_blueprint)  # Main routes (/)
    app.register_blueprint(api_routes_blueprint)  # API routes (/api)
    
    # The data_routes and prediction_routes are already registered with main_blueprint
    # in their respective module files, so we don't need to register them here

    # Log application startup
    logger.info(f"Growatt API v{__version__} initialized")
    
    return app

def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for the application
    
    Args:
        app: Flask application
    """
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"status": "error", "message": "Bad request", "error": str(e)}), 400
        
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Resource not found", "error": str(e)}), 404
        
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"status": "error", "message": "Method not allowed", "error": str(e)}), 405
        
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({
            "status": "error", 
            "message": "Internal server error", 
            "error": str(e) if app.debug else None
        }), 500