# Data Collection Scripts

This directory contains scripts for collecting data from the Growatt API.

## Scripts

- `collect_devices.py` - Collects device information
- `collect_inverter_data.py` - Collects data from inverters
- `devices_data_collector.py` - Collects data from devices
- `collect_all_data.py` - Collects all types of data

## Included Scripts

- **db_data_collector.py** - Main data collector script for Growatt API to database
- **devices_collector.py** - Collects device information only
- **collect_devices.py** - Collects device information and saves to database
- **devices_data_collector.py** - Collects device data (energy, status, etc.)
- **collect_inverter_data.py** - Detailed data collector for inverters
- **offline_devices_notification.py** - Checks for offline devices and sends notifications
- **run_data_collector.sh** - Shell script to run the main data collector
- **run_collectors.py** - Manages running of different collectors
- **fault_logs_collector.py** - Collects fault and alarm logs for all plants and devices
- **run_fault_logs_collector.sh** - Shell script to run the fault logs collector

## Usage

### Fault Logs Collector

The fault logs collector retrieves fault and alarm logs from the Growatt API for all plants and devices, 
and stores them in the database.

```bash
# Run with default settings (collect 7 days of fault logs)
./run_fault_logs_collector.sh

# Collect 14 days of fault logs
./run_fault_logs_collector.sh 14

# Run the Python script directly with more options
python fault_logs_collector.py --days=3 --plant-id=12345 --verbose
```

Command-line options for `fault_logs_collector.py`:

- `--plant-id=ID` - Specific plant ID to collect fault logs for (optional)
- `--days=N` - Number of days to collect fault logs for (default: 7)
- `--verbose` - Enable verbose output
- `--debug` - Print raw API responses for debugging
