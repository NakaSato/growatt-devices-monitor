#!/bin/bash
# Script to run the complete weather data collector with proper environment setup

# Set the script path to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Include configuration from .env file if it exists
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    source "$ENV_FILE"
else
    echo "Warning: No .env file found at $ENV_FILE"
fi

# Default values for configuration
VERBOSE=${VERBOSE:-false}
DRY_RUN=${DRY_RUN:-false}
PLANT_ID=${PLANT_ID:-""}

# Set Python path to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Log file
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/weather_collector_$(date +%Y%m%d_%H%M%S).log"

# Build command with options
CMD="python $SCRIPT_DIR/collect_complete_weather.py"

# Add optional parameters
if [ "$VERBOSE" = "true" ]; then
    CMD="$CMD --verbose"
fi

if [ "$DRY_RUN" = "true" ]; then
    CMD="$CMD --dry-run"
fi

if [ ! -z "$PLANT_ID" ]; then
    CMD="$CMD --plant-id=$PLANT_ID"
fi

# Run the command and log output
echo "Running: $CMD"
echo "Logging to: $LOG_FILE"
echo "Started at: $(date)" | tee -a "$LOG_FILE"
$CMD 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Finished at: $(date)" | tee -a "$LOG_FILE"
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"

exit $EXIT_CODE 