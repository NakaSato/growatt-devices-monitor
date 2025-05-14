### Data Collection Scripts

The following collectors are available in the `scripts/data_collection` directory:

- **Main Data Collector** (`db_data_collector.py`) - Collects energy data from Growatt API
- **Weather Collector** (`../weather/weather_collector.py`) - Collects weather data
- **Fault Logs Collector** (`fault_logs_collector.py`) - Collects fault and alarm logs

These collectors can be run individually or together using the `run_all_collectors.sh` script:

```bash
# Run all collectors with default settings
./run_all_collectors.sh

# Run all collectors with custom settings
./run_all_collectors.sh --days-back=3 --include-weather --include-fault-logs

# Run only specific collectors
./run_all_collectors.sh --no-weather --include-fault-logs

# Run for a specific plant
./run_all_collectors.sh --plant-id=12345
```

## Device Management

The `scripts/collectors/devices_data_collector.py` script allows you to collect device data from the API and manage devices in the database. You can use it to:

- **Collect devices**: Fetch all devices from the API and store them in the database
- **Get device by ID**: Retrieve a device from the database by its serial number
- **Update device by ID**: Update a device's information in the database

You can run the script directly or use the provided `device_manager.sh` wrapper script:

```bash
# Collect all devices
./scripts/collectors/device_manager.sh collect

# Get a device by serial number
./scripts/collectors/device_manager.sh get ABC123456789

# Update a device
./scripts/collectors/device_manager.sh update ABC123456789 --alias "New Device Name" --status "active"

# Update from a JSON file
./scripts/collectors/device_manager.sh update ABC123456789 --from-json update_data.json --show
```

See the [Device Management README](scripts/collectors/README_DEVICE_CLI.md) for more details.