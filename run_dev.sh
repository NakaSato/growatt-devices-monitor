#!/bin/bash
# Start the Growatt API application using Gunicorn in development mode

# Activate virtual environment if it exists
if [ -d "env" ]; then
    echo "Activating virtual environment..."
    source env/bin/activate
fi

# Check if gunicorn is installed, if not, install it
if ! command -v gunicorn &> /dev/null; then
    echo "Gunicorn not found. Installing it now..."
    pip install gunicorn
fi

# Set environment variables for development
export FLASK_ENV=development
export FLASK_APP=wsgi.py
export PYTHONPATH=$(pwd)

# Run with Gunicorn
echo "Starting Growatt API with Gunicorn..."
gunicorn --bind 0.0.0.0:8000 --workers=2 --threads=2 --reload wsgi:app