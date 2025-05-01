#!/bin/bash
# Start the Growatt API application using Gunicorn in development mode
set -e  # Exit immediately if a command exits with a non-zero status

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PORT=8000
WORKERS=2
THREADS=2
WSGI_APP="wsgi:app"
VENV_DIR="env"

echo -e "${GREEN}Starting Growatt API development server...${NC}"

# Check if virtual environment exists
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source "$VENV_DIR/bin/activate" || {
        echo -e "${RED}Failed to activate virtual environment. Exiting.${NC}"
        exit 1
    }
else
    echo -e "${YELLOW}Virtual environment not found at '$VENV_DIR'. Using system Python.${NC}"
fi

# Verify Python version
python_version=$(python3 --version)
echo -e "${GREEN}Using $python_version${NC}"

# Check for required dependencies
echo -e "${GREEN}Checking dependencies...${NC}"
if ! command -v gunicorn &> /dev/null; then
    echo -e "${YELLOW}Gunicorn not found. Installing it now...${NC}"
    pip install gunicorn || {
        echo -e "${RED}Failed to install Gunicorn. Exiting.${NC}"
        exit 1
    }
fi

# Check if wsgi.py exists
if [ ! -f "wsgi.py" ]; then
    echo -e "${RED}wsgi.py not found. Please make sure you're in the correct directory.${NC}"
    exit 1
fi

# Set environment variables for development
export FLASK_ENV=development
export FLASK_APP=wsgi.py
export PYTHONPATH=$(pwd)

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
echo -e "  - Host: 0.0.0.0:$PORT"
echo -e "  - Workers: $WORKERS"
echo -e "  - Threads: $THREADS"
echo -e "  - Auto-reload: Enabled"

# Run with Gunicorn
echo -e "${GREEN}Starting Growatt API with Gunicorn...${NC}"
gunicorn --bind 0.0.0.0:$PORT \
         --workers=$WORKERS \
         --threads=$THREADS \
         --reload \
         --access-logfile=- \
         --error-logfile=- \
         $WSGI_APP