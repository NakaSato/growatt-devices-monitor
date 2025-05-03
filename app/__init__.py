from flask import Flask, jsonify
from flask_caching import Cache
from flask_cors import CORS
import os
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Import Config class which already handles .env loading
from app.config import Config
from app.database import init_db
from app.services.background_service import background_service

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
    
    # Configure 24-hour data collection if enabled
    if app.config.get('ENABLE_24H_COLLECTION', False):
        app.config['DEVICE_DATA_CRON'] = '*/15 * * * *'  # Every 15 minutes all day
        app.config['PLANT_DATA_CRON'] = '*/15 * * * *'   # Every 15 minutes all day
        logger.info("24-hour data collection enabled")
    
    # Always enable background service instead of using cron jobs
    app.config['ENABLE_BACKGROUND_MONITORING'] = True
    
    # Get cache config with proper backend settings
    cache_config = Config.get_cache_config()
    app.config.from_mapping(cache_config)
    
    # Setup directories
    _setup_directories(app)
    
    # Ensure secret key is set
    _configure_secret_key(app)
    
    # Initialize CORS with security settings
    _setup_cors(app)
    
    # Initialize the cache - make it available globally 
    cache = Cache(app)
    
    # Also make the cache available in app context for convenience
    app.cache = cache
    
    # Register context processors for template variables
    _register_context_processors(app)
    
    # Register Jinja filters for templates
    _register_jinja_filters(app)
    
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
    
    # Initialize background monitoring service
    _init_background_service(app)

    # Log application startup
    logger.info(f"\033[32mGrowatt API v{__version__} initialized\033[0m")  # Green color
    logger.info(f"Using cache backend: {app.config.get('CACHE_TYPE', 'Unknown')}")
    logger.info(f"Using scheduler: APScheduler (background mode)")
    
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

def _register_context_processors(app: Flask) -> None:
    """Register context processors for template variables"""
    @app.context_processor
    def inject_now():
        """
        Inject current timestamp and other time-related variables for use in templates.
        This is particularly useful for cache busting on static file URLs.
        """
        return {
            'now': int(time.time()),  # Unix timestamp for cache busting
            'current_time': time.strftime('%Y-%m-%d %H:%M:%S')  # Formatted time for display
        }

def _register_jinja_filters(app: Flask) -> None:
    """Register custom Jinja2 filters for templates"""
    @app.template_filter('static_url')
    def static_url_filter(file_path):
        """
        Add cache-busting timestamp to static file URLs.
        
        Usage in templates:
            {{ 'js/app.js'|static_url }}
            
        Output:
            /static/js/app.js?_ts=1620000000
        """
        from flask import url_for
        timestamp = str(int(time.time()))
        url = url_for('static', filename=file_path)
        return f"{url}?_ts={timestamp}"

def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints"""
    from app.routes import main_blueprint, api_routes_blueprint, device_status_routes, prediction_routes, data_routes
    from app.routes.operations.operations_routes import operations_routes
    from app.routes.operations.scheduler_routes import scheduler_routes
    from app.routes.diagnosis import diagnosis_routes
    
    # Register all blueprints
    app.register_blueprint(main_blueprint)  # Main routes (/)
    app.register_blueprint(api_routes_blueprint)  # API routes (/api)
    app.register_blueprint(operations_routes)  # Operations routes (/api/operations)
    app.register_blueprint(scheduler_routes)  # Scheduler routes (/api/scheduler)
    app.register_blueprint(device_status_routes)  # Device status routes
    app.register_blueprint(prediction_routes)  # Prediction routes
    app.register_blueprint(diagnosis_routes)  # Diagnosis routes
    app.register_blueprint(data_routes)  # Data routes

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

def _init_background_service(app: Flask) -> None:
    """Initialize the background monitoring service with the current app"""
    try:
        logger.info("Initializing background monitoring service with APScheduler")
        
        # Ensure background service is always enabled
        app.config['ENABLE_BACKGROUND_MONITORING'] = True
        
        # Configure APScheduler settings if not already configured
        if 'SCHEDULER_API_ENABLED' not in app.config:
            app.config['SCHEDULER_API_ENABLED'] = True
        
        if 'SCHEDULER_TIMEZONE' not in app.config:
            app.config['SCHEDULER_TIMEZONE'] = app.config.get('TIMEZONE', 'UTC')
            
        # Job store configuration
        if app.config.get('USE_SQLALCHEMY_JOBSTORE', False) and 'SCHEDULER_JOBSTORES' not in app.config:
            try:
                from app.database import get_db_url
                app.config['SCHEDULER_JOBSTORES'] = {
                    'default': {
                        'type': 'sqlalchemy', 
                        'url': get_db_url()
                    }
                }
                logger.info("Configured SQLAlchemy jobstore for persistent jobs")
            except Exception as e:
                logger.warning(f"Could not configure SQLAlchemy jobstore: {e}")
        
        # Configure default job executors if not set
        if 'SCHEDULER_EXECUTORS' not in app.config:
            app.config['SCHEDULER_EXECUTORS'] = {
                'default': {'type': 'threadpool', 'max_workers': 20}
            }
            
        # Configure default job settings if not set
        if 'SCHEDULER_JOB_DEFAULTS' not in app.config:
            app.config['SCHEDULER_JOB_DEFAULTS'] = {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 120  # 2 minutes
            }
        
        # Initialize the background service with the app
        background_service.init_app(app)
        logger.info(f"Background monitoring service initialized with timezone: {app.config.get('SCHEDULER_TIMEZONE')}")
        
        # Log enabled scheduler features
        if app.config.get('USE_SQLALCHEMY_JOBSTORE', False):
            logger.info("Using persistent SQLAlchemy jobstore for scheduler")
        
        # Log the enabled monitoring tasks
        if app.config.get('MONITOR_DEVICE_STATUS', True):
            interval = app.config.get('DEVICE_STATUS_CHECK_INTERVAL_MINUTES', 5)
            logger.info(f"Device status monitoring enabled (every {interval} minutes)")
        
        if app.config.get('COLLECT_DEVICE_DATA', True):
            cron = app.config.get('DEVICE_DATA_CRON', '*/15 6-20 * * *')
            logger.info(f"Device data collection enabled (schedule: {cron})")
        
        if app.config.get('COLLECT_PLANT_DATA', True):
            cron = app.config.get('PLANT_DATA_CRON', '*/15 6-20 * * *')
            logger.info(f"Plant data collection enabled (schedule: {cron})")
            
        if app.config.get('SEND_OFFLINE_NOTIFICATIONS', True):
            cron = app.config.get('OFFLINE_NOTIFICATIONS_CRON', '0 9,17 * * *')
            logger.info(f"Offline device notifications enabled (schedule: {cron})")
        
        # Store background service instance in app for access from routes/API
        app.background_service = background_service
        
        # Log success message
        logger.info("APScheduler background service successfully initialized and running")
    except Exception as e:
        logger.error(f"Failed to initialize background service: {e}")
        logger.warning("Background monitoring will not be available")
        
        # Still store the instance so routes don't break
        app.background_service = background_service