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