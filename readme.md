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
