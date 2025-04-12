from flask import Flask
from flask_caching import Cache

def create_app():
    config = {
        'DEBUG': True,
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000,
    }
    app = Flask(__name__)
    app.config.from_mapping(config)
    cache = Cache(app)
    # Initialize the cache
    cache.init_app(app)

    # Import and register routes
    from app.routes import api_blueprint
    app.register_blueprint(api_blueprint)

    return app