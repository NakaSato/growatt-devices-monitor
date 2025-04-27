#!/usr/bin/env python3
"""
WSGI Entry Point for Koyeb Deployment
"""
from app import create_app

# Create the Flask application instance
application = create_app()

# For Gunicorn to use
app = application

if __name__ == "__main__":
    app.run()