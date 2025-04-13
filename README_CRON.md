# Setting Up Automated Data Synchronization

This guide explains how to set up automatic data synchronization with the Growatt API using cron jobs.

## Requirements

Before setting up the cron job, make sure you have:

1. Installed the required Python package:

   ```
   pip install python-crontab
   ```

2. Made sure the data_sync.py script is working correctly when run manually

## Setting Up the Cron Job

We provide a utility script that makes it easy to set up cron jobs.

### Basic Usage

To set up an hourly cron job:

```bash
python setup_cron.py
```

### Options

- Set different intervals:

  ```bash
  python setup_cron.py --interval daily    # Run once a day at 1:00 AM
  python setup_cron.py --interval hourly   # Run every hour
  python setup_cron.py --interval every6h  # Run every 6 hours
  python setup_cron.py --interval every12h # Run every 12 hours
  ```

- List current cron jobs:

  ```bash
  python setup_cron.py --list
  ```

- Remove all Growatt API cron jobs:

  ```bash
  python setup_cron.py --remove
  ```

- Specify a different user (requires proper permissions):
  ```bash
  sudo python setup_cron.py --user someuser
  ```

## Manual Setup

If you prefer to set up the cron job manually:

1. Open your crontab:

   ```bash
   crontab -e
   ```

2. Add one of the following lines:

   - For hourly sync:

     ```
     0 * * * * /usr/bin/python3 /path/to/growatt-api/data_sync.py >> /path/to/growatt-api/cron_sync.log 2>&1
     ```

   - For daily sync at 1:00 AM:
     ```
     0 1 * * * /usr/bin/python3 /path/to/growatt-api/data_sync.py >> /path/to/growatt-api/cron_sync.log 2>&1
     ```

## Logs

Logs from cron job execution will be saved to:

1. `data_sync.log` - Contains the application logs
2. `cron_sync.log` - Contains the output that would normally go to stdout/stderr

## Troubleshooting

If your cron job isn't running properly:

1. Check if the script has execute permissions:

   ```bash
   chmod +x data_sync.py run_sync.sh
   ```

2. Verify your cron service is running:

   ```bash
   systemctl status cron  # On most Linux systems
   ```

3. Check the log files for errors

4. Try running the wrapper script manually to see if there are any issues:
   ```bash
   ./run_sync.sh
   ```

## Running the Test Data Collector

For testing purposes, you can run the data collector in test mode which simulates API responses without making actual API calls.

### Basic Test Usage

```bash
python data_sync.py --test
```

### Test Options

- Collect specific data types:

  ```bash
  python data_sync.py --test --collect daily     # Collect only daily data
  python data_sync.py --test --collect monthly   # Collect only monthly data
  python data_sync.py --test --collect all       # Collect all data types (default)
  ```

- Simulate specific dates:

  ```bash
  python data_sync.py --test --date 2023-12-25   # Simulate data for a specific date
  ```

- Generate verbose output:

  ```bash
  python data_sync.py --test --verbose           # Show detailed progress and data
  ```

- Test database connections without saving data:
  ```bash
  python data_sync.py --test --dry-run           # Test process without saving data
  ```

### Viewing Test Results

After running the test data collector, you can check the following logs:

1. `data_sync_test.log` - Contains the test application logs
2. `test_data/` directory - Contains any generated test data files

Test mode is useful for:

- Debugging the data collection process
- Testing database connections and schema compatibility
- Verifying data transformation logic
- Testing the system without consuming API rate limits
