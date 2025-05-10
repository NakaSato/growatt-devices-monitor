#!/bin/bash
# Run All Collectors
# This script runs all data collectors in the proper sequence
#
# Usage: ./run_all_collectors.sh [options]
#
# Options:
#   --days-back=N       Number of days of historical data to collect (default: 7)
#   --include-weather   Include weather data collection (default: true)
#   --include-fault-logs Include fault logs collection (default: true)
#   --verbose           Enable verbose output (default: false)
#   --dry-run           Run without saving to database (default: false)
#   --plant-id=ID       Specific plant ID to collect data for
#   --help              Show this help message

# Set the script path to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DAYS_BACK=${DAYS_BACK:-7}
INCLUDE_WEATHER=${INCLUDE_WEATHER:-true}
INCLUDE_FAULT_LOGS=${INCLUDE_FAULT_LOGS:-true}
VERBOSE=${VERBOSE:-false}
DRY_RUN=${DRY_RUN:-false}
PLANT_ID=${PLANT_ID:-""}

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        --days-back=*)
            DAYS_BACK="${1#*=}"
            ;;
        --include-weather)
            INCLUDE_WEATHER=true
            ;;
        --no-weather)
            INCLUDE_WEATHER=false
            ;;
        --include-fault-logs)
            INCLUDE_FAULT_LOGS=true
            ;;
        --no-fault-logs)
            INCLUDE_FAULT_LOGS=false
            ;;
        --verbose)
            VERBOSE=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --plant-id=*)
            PLANT_ID="${1#*=}"
            ;;
        --help)
            echo "Usage: ./run_all_collectors.sh [options]"
            echo ""
            echo "Options:"
            echo "  --days-back=N       Number of days of historical data to collect (default: 7)"
            echo "  --include-weather   Include weather data collection (default: true)"
            echo "  --no-weather        Exclude weather data collection"
            echo "  --include-fault-logs Include fault logs collection (default: true)"
            echo "  --no-fault-logs     Exclude fault logs collection"
            echo "  --verbose           Enable verbose output (default: false)"
            echo "  --dry-run           Run without saving to database (default: false)"
            echo "  --plant-id=ID       Specific plant ID to collect data for"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help for usage information"
            exit 1
            ;;
    esac
    shift
done

# Include configuration from .env file if it exists
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    source "$ENV_FILE"
else
    echo "Warning: No .env file found at $ENV_FILE"
fi

# Export variables so they're available to child scripts
export DAYS_BACK
export INCLUDE_WEATHER
export INCLUDE_FAULT_LOGS
export VERBOSE
export DRY_RUN
export PLANT_ID

# Log directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/all_collectors_$(date +%Y%m%d_%H%M%S).log"

# Start logging
echo "=======================================================" | tee -a "$LOG_FILE"
echo "Starting All Collectors at $(date)" | tee -a "$LOG_FILE"
echo "=======================================================" | tee -a "$LOG_FILE"
echo "Configuration:" | tee -a "$LOG_FILE"
echo "  Days Back: $DAYS_BACK" | tee -a "$LOG_FILE"
echo "  Include Weather: $INCLUDE_WEATHER" | tee -a "$LOG_FILE"
echo "  Include Fault Logs: $INCLUDE_FAULT_LOGS" | tee -a "$LOG_FILE"
echo "  Verbose: $VERBOSE" | tee -a "$LOG_FILE"
echo "  Dry Run: $DRY_RUN" | tee -a "$LOG_FILE"
if [ ! -z "$PLANT_ID" ]; then
    echo "  Plant ID: $PLANT_ID" | tee -a "$LOG_FILE"
fi
echo "=======================================================" | tee -a "$LOG_FILE"

# 1. Run the main data collector
echo "" | tee -a "$LOG_FILE"
echo "STEP 1: Running main data collector..." | tee -a "$LOG_FILE"
$SCRIPT_DIR/data_collection/run_data_collector.sh 2>&1 | tee -a "$LOG_FILE"
DATA_COLLECTOR_EXIT_CODE=${PIPESTATUS[0]}

# 2. Run the weather collector (if enabled)
WEATHER_COLLECTOR_EXIT_CODE=0
if [ "$INCLUDE_WEATHER" = "true" ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "STEP 2: Running weather collector..." | tee -a "$LOG_FILE"
    $SCRIPT_DIR/weather/run_weather_collector.sh 2>&1 | tee -a "$LOG_FILE"
    WEATHER_COLLECTOR_EXIT_CODE=${PIPESTATUS[0]}
else
    echo "" | tee -a "$LOG_FILE"
    echo "STEP 2: Weather collector skipped (disabled)" | tee -a "$LOG_FILE"
fi

# 3. Run the fault logs collector (if enabled)
FAULT_LOGS_COLLECTOR_EXIT_CODE=0
if [ "$INCLUDE_FAULT_LOGS" = "true" ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "STEP 3: Running fault logs collector..." | tee -a "$LOG_FILE"
    $SCRIPT_DIR/data_collection/run_fault_logs_collector.sh $DAYS_BACK 2>&1 | tee -a "$LOG_FILE"
    FAULT_LOGS_COLLECTOR_EXIT_CODE=${PIPESTATUS[0]}
else
    echo "" | tee -a "$LOG_FILE"
    echo "STEP 3: Fault logs collector skipped (disabled)" | tee -a "$LOG_FILE"
fi

# 4. Run any other collector scripts
# Add additional collectors here as needed

# Log completion
echo "" | tee -a "$LOG_FILE"
echo "=======================================================" | tee -a "$LOG_FILE"
echo "All collectors completed at $(date)" | tee -a "$LOG_FILE"
echo "Main data collector exit code: $DATA_COLLECTOR_EXIT_CODE" | tee -a "$LOG_FILE"
if [ "$INCLUDE_WEATHER" = "true" ]; then
    echo "Weather collector exit code: $WEATHER_COLLECTOR_EXIT_CODE" | tee -a "$LOG_FILE"
fi
if [ "$INCLUDE_FAULT_LOGS" = "true" ]; then
    echo "Fault logs collector exit code: $FAULT_LOGS_COLLECTOR_EXIT_CODE" | tee -a "$LOG_FILE"
fi
echo "=======================================================" | tee -a "$LOG_FILE"

# Determine overall exit code (non-zero if any collector failed)
if [ $DATA_COLLECTOR_EXIT_CODE -ne 0 ] || [ $WEATHER_COLLECTOR_EXIT_CODE -ne 0 ] || [ $FAULT_LOGS_COLLECTOR_EXIT_CODE -ne 0 ]; then
    echo "WARNING: One or more collectors failed!" | tee -a "$LOG_FILE"
    exit 1
else
    echo "SUCCESS: All collectors completed successfully" | tee -a "$LOG_FILE"
    exit 0
fi 