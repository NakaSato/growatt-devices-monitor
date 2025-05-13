#!/bin/bash
# ========================================================================
# Growatt Devices Data Collection Script
# 
# This script runs the devices data collection for Growatt monitoring.
# It can be used for manual execution or scheduled with cron.
# ========================================================================

# Set the base directory to the script's location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to the project root directory
cd "$PROJECT_ROOT"

# Create timestamp for file naming
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Configure output paths
OUTPUT_DIR="$PROJECT_ROOT/data/devices"
OUTPUT_FILE="devices_$TIMESTAMP.json"
LOG_FILE="$PROJECT_ROOT/logs/devices_collection_$TIMESTAMP.log"

# Create necessary directories
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$OUTPUT_DIR"

# Set Python path to include project root
export PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT"

# Load environment variables if .env file exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading environment variables from .env file"
    source <(grep -v '^#' "$PROJECT_ROOT/.env" | sed -E 's/(.*)=(.*)$/export \1="\2"/g')
fi

# Run the data collection script and log output
echo "Starting Growatt devices data collection at $(date)"
echo "Output file: $OUTPUT_DIR/$OUTPUT_FILE"
echo "Log file: $LOG_FILE"

# Execute the collection script
python "$PROJECT_ROOT/scripts/collectors/collect_devices.py" \
    --output-dir "$OUTPUT_DIR" \
    --output "$OUTPUT_FILE" \
    --verbose \
    2>&1 | tee -a "$LOG_FILE"

# Check if the collection was successful
EXIT_CODE=${PIPESTATUS[0]}
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Devices data collection completed successfully at $(date)"
    echo "Data saved to: $OUTPUT_DIR/$OUTPUT_FILE"
else
    echo "❌ Devices data collection failed with exit code $EXIT_CODE at $(date)"
fi

# If you want to keep only recent files, uncomment and adjust these lines
# Find and delete files older than 7 days
# find "$OUTPUT_DIR" -name "devices_*.json" -type f -mtime +7 -delete
# find "$PROJECT_ROOT/logs" -name "devices_collection_*.log" -type f -mtime +7 -delete

exit $EXIT_CODE
