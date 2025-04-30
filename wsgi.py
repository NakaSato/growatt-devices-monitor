#!/usr/bin/env python3
"""
WSGI Entry Point for Production Deployment

This module creates the Flask application instance that will be used
by Gunicorn or other WSGI servers.
"""
import os
import sys

# Add the project root directory to the Python path
# This ensures the app module can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app import create_app

# Create the Flask application instance
application = create_app()

# For Gunicorn to use
app = application

if __name__ == "__main__":
    app.run()