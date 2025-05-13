#!/bin/bash
# ========================================================================
# Setup Cron Job for Growatt Devices Collection
# 
# This script sets up a cron job to run the devices data collection
# every 15 minutes between 6 AM and 7 PM.
# ========================================================================

# Set the base directory to the script's location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Path to the devices collector script
COLLECTOR_SCRIPT="$SCRIPT_DIR/run_devices_collector.sh"

# Ensure the collector script is executable
chmod +x "$COLLECTOR_SCRIPT"

# Create a temporary file for the crontab
TEMP_CRONTAB=$(mktemp)

# Get current crontab content
crontab -l > "$TEMP_CRONTAB" 2>/dev/null

# Check if the cron job already exists
if grep -q "run_devices_collector.sh" "$TEMP_CRONTAB"; then
    echo "Cron job for devices collector already exists. Skipping."
else
    # Add the cron job to run every 15 minutes from 6 AM to 7 PM
    echo "# Growatt Devices Collection - every 15 minutes from 6 AM to 7 PM" >> "$TEMP_CRONTAB"
    echo "*/15 6-19 * * * $COLLECTOR_SCRIPT" >> "$TEMP_CRONTAB"
    
    # Install the new crontab
    crontab "$TEMP_CRONTAB"
    
    echo "Cron job for devices collector has been added. Schedule: every 15 minutes from 6 AM to 7 PM."
fi

# Clean up the temporary file
rm "$TEMP_CRONTAB"

echo "Cron setup complete. You can verify it with 'crontab -l'"

# Optional: Show the current crontab
echo "Current crontab:"
crontab -l
