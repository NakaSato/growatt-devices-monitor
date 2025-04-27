#!/usr/bin/env python3
"""
Growatt Devices Monitor - Main Application Entry Point

This module initializes and runs the Flask application.
"""

import argparse
import logging
import os
import sys
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the Growatt Devices Monitor application')
    parser.add_argument(
        '--host', 
        default='0.0.0.0',
        help='Host to run the application on (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=8000,
        help='Port to run the application on (default: 8000)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Run in debug mode'
    )
    parser.add_argument(
        '--reload', 
        action='store_true',
        help='Enable hot reloading when files change'
    )
    parser.add_argument(
        '--live-reload', 
        action='store_true',
        help='Enable browser live reload for static files changes'
    )
    parser.add_argument(
        '--template-reload', 
        action='store_true',
        help='Enable explicit hot reloading for template changes'
    )
    return parser.parse_args()

def main():
    """Initialize and run the application."""
    args = parse_args()
    
    # Check if required environment variables are set
    if not os.getenv('GROWATT_USERNAME') or not os.getenv('GROWATT_PASSWORD'):
        logger.warning("GROWATT_USERNAME or GROWATT_PASSWORD environment variables not set.")
        logger.warning("You will need to provide these credentials in the application.")
    
    try:
        # Create the Flask application
        app = create_app()
        
        # Configure for development with hot reloading
        if args.debug or args.live_reload:
            # Disable static file caching in development
            app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
            # Store live reload setting in app config for template access
            app.config['LIVE_RELOAD_ENABLED'] = True
            logger.info("Live reload for static files enabled")
        
        # Enable explicit template reloading if requested
        if args.template_reload or args.debug:
            app.config['TEMPLATES_AUTO_RELOAD'] = True
            logger.info("Template auto-reload enabled")
        
        # Run the application
        logger.info(f"Starting Growatt Devices Monitor on {args.host}:{args.port}")
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.reload or args.debug  # Enable hot reloading if --reload or --debug is set
        )
        return 0
    except Exception as e:
        logger.exception(f"Failed to start application: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
