# Growatt API Integration

A Python application for collecting, analyzing, and visualizing data from Growatt solar inverters and energy storage systems. This project provides a simple way to access your Growatt data, store it locally, and perform basic analytics.

## Features

- **Data Collection**: Automatically fetch data from Growatt API including plant, device, energy, and weather information
- **Local Database**: Store all your historical solar data in a local SQLite database
- **Automated Syncing**: Configure scheduled data synchronization using cron jobs
- **Web Dashboard**: View your solar production data through a simple web interface
- **Energy Predictions**: Basic ML-based predictions for future energy production
- **Test Mode**: Simulate data collection without making actual API calls

## Getting Started

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- Growatt account credentials

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/growatt-api.git
   cd growatt-api
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your Growatt credentials by either:

   - Setting environment variables:
     ```bash
     export GROWATT_USERNAME="your_username"
     export GROWATT_PASSWORD="your_password"
     ```
   - OR modify the credentials in `app/utils.py` (less secure, for development only)

4. Initialize the database:
   ```bash
   python data_sync.py --init
   ```

## Growatt API Data Sync

A tool to sync data from Growatt solar inverter API to a local SQLite database.

### Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - requests
  - sqlite3 (usually included with Python)

You can install the required packages using:

```bash
pip install requests
```

### First-time Setup

Before using the sync tool, you need to initialize the data storage and configuration:

```bash
python3 data_sync.py --init
```

This will:

- Create the necessary directory structure
- Generate a configuration file (`growatt_sync_config.json`)
- Set up the SQLite database

After initialization, you need to edit the config file to add your Growatt API credentials:

```bash
nano growatt_sync_config.json
```

Update the `api_settings` section with your username and password:

```json
"api_settings": {
  "url": "https://server.growatt.com",
  "username": "your_username",
  "password": "your_password",
  "max_retries": 3,
  "retry_delay": 5
}
```

### Regular Data Sync

To sync data from the Growatt API to your local database:

```bash
python3 data_sync.py
```

This will:

- Log in to the Growatt API using your credentials
- Fetch plant, device, energy, and weather data
- Store the data in the SQLite database
- Create a backup of the database before making changes

### Database Setup Only

If you need to reset or recreate just the database:

```bash
python3 data_sync.py --setup-db
```

This will create the required tables in the SQLite database without changing other files.

### Advanced Options

#### Verbose Logging

For more detailed logging information:

```bash
python3 data_sync.py --verbose
```

#### Custom Data Directory

To specify a custom directory for data storage during initialization:

```bash
python3 data_sync.py --init --dir /path/to/custom/directory
```

### Using the Wrapper Script

For automated use (e.g., in cron jobs), the `run_sync.sh` script provides additional features:

```bash
./run_sync.sh
```

Make the script executable first:

```bash
chmod +x run_sync.sh
```

The wrapper script includes:

- Lock file to prevent multiple simultaneous runs
- Log rotation
- Environment detection
- Error handling and reporting

### Configuration

The `growatt_sync_config.json` file contains several settings you can adjust:

- `sync_settings.days_history`: Number of days of historical data to retrieve (default: 7)
- `sync_settings.*_sync_interval_hours`: How often different data types should be synced
- `api_settings.max_retries`: Number of retries for failed API calls
- `api_settings.retry_delay`: Delay between retry attempts in seconds

## Troubleshooting

If you encounter issues:

1. Check your API credentials in the config file
2. Run with verbose logging: `python3 data_sync.py --verbose`
3. Check if the Growatt API is available
4. Ensure you have proper file permissions in the data directory

## Data Collection and Database Operations

### Collecting Data

To collect data from Growatt API and store it in the database:

```bash
# Basic data collection
python data_sync.py

# Collect with detailed logs
python data_sync.py --verbose

# Collect specific data types
python data_sync.py --collect daily
python data_sync.py --collect monthly
python data_sync.py --collect all
```

### Database Management

```bash
# Initialize or reset the database
python data_sync.py --init

# Export collected data to CSV
python data_sync.py --export path/to/export/folder

# Verify database integrity
python data_sync.py --verify
```

### Automating Data Collection

For regular data collection, set up a cron job:

```bash
# Configure hourly data collection
python setup_cron.py --interval hourly
```

Or manually add to your crontab:

```bash
# Run every hour
0 * * * * /path/to/growatt-api/run_sync.sh
```

## Usage

### Running the Web Interface

Start the web server:

```bash
python -m app.main
```

Then access the dashboard at http://localhost:5000

### Manual Data Synchronization

To manually sync data from Growatt API:

```bash
python data_sync.py
```

Options:

- `--verbose` or `-v`: Show detailed output
- `--init`: Initialize the database before syncing

### Scheduled Data Collection

Set up automatic data collection using the provided script:

```bash
python setup_cron.py --interval hourly
```

Available intervals:

- `hourly`: Run every hour
- `daily`: Run once a day at 1:00 AM
- `every6h`: Run every 6 hours
- `every12h`: Run every 12 hours

See [CRON_README.md](README_CRON.md) for more detailed information about setting up cron jobs.

### Test Mode

Run the system in test mode to generate simulated data:

```bash
python data_sync.py --test
```

Test options:

- `--collect [daily|monthly|yearly|all]`: Specify which data types to simulate
- `--date YYYY-MM-DD`: Simulate data for a specific date
- `--dry-run`: Run without saving data to the database

## Project Structure

```
growatt-api/
├── app/                    # Application code
│   ├── core/               # Core API client
│   ├── data/               # Database storage
│   ├── ml/                 # Machine learning models
│   ├── routes/             # API routes
│   ├── views/              # Web UI templates
│   ├── __init__.py         # App initialization
│   ├── data_collector.py   # Data collection logic
│   ├── database.py         # Database interface
│   ├── main.py             # Web app entry point
│   └── utils.py            # Utility functions
├── test_data/              # Test data storage
├── data_sync.py            # Data sync script
├── run_sync.sh             # Sync shell wrapper
├── setup_cron.py           # Cron job setup
└── README.md               # This file
```

## API Endpoints

The application provides several API endpoints:

- `/api/plants` - Get all plants
- `/api/devices` - Get all devices
- `/api/weather` - Get weather data
- `/api/prediction` - Get energy production predictions
- `/api/data/collect` - Manually trigger data collection

## Development

### Running Tests

```bash
python -m unittest discover tests
```

### Adding New Features

1. Follow the existing code structure
2. Add new routes in the appropriate route file
3. Update documentation for any new features

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Make sure your Growatt credentials are correct
2. **Database Errors**: Check that the database has been initialized with `--init`
3. **Cron Job Not Running**: Verify that `run_sync.sh` has execute permissions

### Logs

Check these log files for troubleshooting:

- `data_sync.log` - Main application logs
- `cron_sync.log` - Logs from cron job execution

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Growatt API](https://server.growatt.com/) for providing the data access
- Contributors to this project
