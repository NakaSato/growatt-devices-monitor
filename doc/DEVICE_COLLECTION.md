# Device Data Collection and Management

This document explains how to collect, manage, and update device data in the system.

## Overview

The system provides several ways to interact with device data:

1. **Collect Device Data**: Fetches device information from the API and stores it in the database
2. **Export Device Data**: Exports device data from the database to JSON files
3. **Get Device Information**: Retrieves information about a specific device by its serial number
4. **Update Device Information**: Updates device information in the database

## Command Line Tools

### Basic Device Collection

To collect device data from the API and store it in the database:

```bash
python scripts/collectors/collect_devices_data.py collect
```

### Export Device Data

To export all devices from the database to a JSON file:

```bash
python scripts/collectors/collect_devices_data.py export --output data/devices/my_export.json
```

### Get Device Information

To retrieve information about a specific device:

```bash
# Get in formatted text output
python scripts/collectors/collect_devices_data.py get SERIAL_NUMBER

# Get in JSON format
python scripts/collectors/collect_devices_data.py get SERIAL_NUMBER --json
```

### Update Device Information

To update information for a specific device:

```bash
# Update basic fields
python scripts/collectors/collect_devices_data.py update SERIAL_NUMBER --alias "New Name" --status "active"

# Update using a JSON file
python scripts/collectors/collect_devices_data.py update SERIAL_NUMBER --from-json update_data.json --show
```

## Using the Shell Scripts

For convenience, we provide shell scripts that can perform common operations:

### Device Collection Shell Script

The `run_device_collection.sh` script simplifies the device data collection process:

```bash
# Collect and export all devices
./scripts/collectors/run_device_collection.sh --action collect

# Export-only mode (no API calls)
./scripts/collectors/run_device_collection.sh --action export-only

# Get a specific device
DEVICE_ID="SERIAL_NUMBER" ./scripts/collectors/run_device_collection.sh --action get-device

# Enable debug mode
./scripts/collectors/run_device_collection.sh --action collect --debug
```

### Device Manager Shell Script

The `device_manager.sh` script provides a user-friendly command-line interface:

```bash
# Collect all devices
./scripts/collectors/device_manager.sh collect

# Get device by ID
./scripts/collectors/device_manager.sh get SERIAL_NUMBER

# Update a device
./scripts/collectors/device_manager.sh update SERIAL_NUMBER --alias "New Name"
```

## GitHub Actions Workflow

The system includes a GitHub Actions workflow that automatically collects device data on a schedule and supports manual triggering with different modes:

1. **Collect Mode**: Fetches data from the API and stores it in the database (default)
2. **Export-Only Mode**: Exports existing database data without making API calls
3. **Get-Device Mode**: Retrieves information about a specific device by ID

To manually trigger the workflow, go to the Actions tab in GitHub and select the "Growatt Devices Collection" workflow.

## Troubleshooting

If you encounter issues with the device data collection:

1. Enable debug mode with the `--debug` flag
2. Check the log files in the `logs/` directory
3. Make sure your API credentials are correctly set in the environment variables
4. Verify the database connection is working correctly
