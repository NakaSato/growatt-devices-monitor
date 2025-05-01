from flask import Flask, jsonify
from flask_caching import Cache
from flask_cors import CORS
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Import Config class which already handles .env loading
from app.config import Config
from app.database import init_db

# Define version
__version__ = "1.0.0"

# Configure logging using values from Config
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global cache instance that will be initialized in create_app
cache: Optional[Cache] = None

def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Create and configure the Flask application
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Flask: Configured Flask application
    """
    global cache
    
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
    
    # Configure the app with cache settings from Config
    app.config.from_mapping(Config.get_cache_config())
    
    # Setup directories
    _setup_directories(app)
    
    # Ensure secret key is set
    _configure_secret_key(app)
    
    # Initialize CORS with security settings
    _setup_cors(app)
    
    # Initialize the cache
    cache = Cache(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Initialize database
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Continue without database if it fails in development mode
            if not app.config.get('DEBUG', False):
                raise
    
    # Import and register routes
    _register_blueprints(app)

    # Log application startup
    logger.info(f"\033[32mGrowatt API v{__version__} initialized\033[0m")  # Green color
    
    return app

def _setup_directories(app: Flask) -> None:
    """Set up necessary directories for the application"""
    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Ensure data directory exists
    data_dir = Path(app.root_path) / 'data'
    os.makedirs(data_dir, exist_ok=True)

def _configure_secret_key(app: Flask) -> None:
    """Ensure a secret key is set for the application"""
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.urandom(24)
        logger.warning('No SECRET_KEY set, using a random one for this session')

def _setup_cors(app: Flask) -> None:
    """Configure CORS for the application with secure settings"""
    # Only allow CORS for API routes with configurable origins
    origins = app.config.get('CORS_ORIGINS', '*')
    CORS(app, resources={r"/api/*": {"origins": origins}})

def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints"""
    from app.routes import main_blueprint, api_routes_blueprint, data_routes, prediction_routes
    
    # Register all blueprints
    app.register_blueprint(main_blueprint)  # Main routes (/)
    app.register_blueprint(api_routes_blueprint)  # API routes (/api)
    
    # Note: data_routes and prediction_routes are already registered with main_blueprint

def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for the application
    
    Args:
        app: Flask application
    """
    @app.errorhandler(400)
    def bad_request(e):
        logger.warning(f"Bad request: {str(e)}")
        return jsonify({"status": "error", "message": "Bad request", "error": str(e)}), 400
        
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Resource not found", "error": str(e)}), 404
        
    @app.errorhandler(405)
    def method_not_allowed(e):
        logger.warning(f"Method not allowed: {str(e)}")
        return jsonify({"status": "error", "message": "Method not allowed", "error": str(e)}), 405
        
    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": "Internal server error", 
            "error": str(e) if app.debug else None
        }), 500