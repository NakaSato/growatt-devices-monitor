#!/bin/bash
# Run Fault Logs Collector
#
# This script runs the fault logs collector to update the database with fault logs
# from Growatt devices.
#
# Usage:
#   ./run_fault_logs_collector.sh [days]
#
# Options:
#   days   Number of days of historical fault logs to collect (default: 7)

# Set default days if not provided
DAYS=${1:-7}

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory to ensure relative paths work
cd "${SCRIPT_DIR}"

# Load environment variables if .env file exists
ENV_FILE="../../.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set up logging
LOG_DIR="../../logs"
LOG_FILE="${LOG_DIR}/fault_logs_collector.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Run the setup for fault logs table if it doesn't exist yet
echo "Setting up fault logs table if needed..."
python ../database/create_fault_logs_table.py

# Print message about running the collector
echo "Running Fault Logs Collector for the last $DAYS days..."
echo "Logs will be saved to $LOG_FILE"

# Run the fault logs collector with python
python fault_logs_collector.py --days=$DAYS --verbose 2>&1 | tee -a "$LOG_FILE"

# Check if the command executed successfully
if [ $? -eq 0 ]; then
    echo "Fault logs collection completed successfully."
    exit 0
else
    echo "Fault logs collection failed."
    exit 1
fi 