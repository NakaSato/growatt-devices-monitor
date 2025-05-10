# Growatt Scripts

This directory contains scripts for the Growatt Devices Monitor application.

## Directory Structure

- `data_collection/` - Scripts for collecting data from Growatt API
- `weather/` - Scripts for collecting and processing weather data
- `database/` - Scripts for database operations and maintenance
- `reports/` - Scripts for generating reports from collected data
- `utils/` - Utility scripts used by other parts of the application
- `cron/` - Scripts for scheduling and running tasks
- `notifications/` - Scripts for sending notifications
- `setup/` - Scripts for setting up and configuring the application

## Environment Setup

Create a `.env` file in the project root with the following environment variables:

```bash
# Growatt API credentials
GROWATT_USERNAME=your_username
GROWATT_PASSWORD=your_password

# PostgreSQL configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=growattdb
POSTGRES_USER=growatt
POSTGRES_PASSWORD=your_password

# Data collection configuration
DAYS_BACK=7           # Number of days of history to collect
INCLUDE_WEATHER=true  # Whether to include weather data
VERBOSE=false         # Enable verbose output
```

## Common Usage

### Data Collection

```bash
# Run all collectors in the proper sequence
./run_all_collectors.sh

# Or run individual collectors:

# Collect all data
./data_collection/run_data_collector.sh

# Collect weather data
./weather/run_weather_collector.sh

# With specific options
DAYS_BACK=3 VERBOSE=true ./data_collection/run_data_collector.sh

# For a specific plant
PLANT_ID=10031698 ./weather/run_weather_collector.sh
```

### Scheduling

Check `cron/crontab.example` for recommended scheduling configurations.
