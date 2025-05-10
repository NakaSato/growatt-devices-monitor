#!/usr/bin/env python3
"""
Organize Scripts

This script organizes the scripts directory by moving files into appropriate subdirectories
based on their functionality.

Usage:
    python organize_scripts.py [--dry-run]

Options:
    --dry-run    Show what would be moved without actually moving files
"""

import os
import sys
import shutil
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Organize scripts into appropriate subdirectories')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be moved without actually moving files')
    return parser.parse_args()

def create_directories(scripts_dir, dry_run=False):
    """Create the necessary subdirectories"""
    directories = [
        'data_collection',  # For scripts that collect data
        'weather',          # For weather-related scripts
        'database',         # For database-related scripts
        'reports',          # For report-generation scripts
        'utils',            # For utility scripts
        'cron',             # For cron and scheduled scripts
        'notifications',    # For notification scripts
        'setup'             # For setup scripts
    ]
    
    created_dirs = []
    
    for directory in directories:
        dir_path = os.path.join(scripts_dir, directory)
        if not os.path.exists(dir_path):
            if not dry_run:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
            else:
                logger.info(f"Would create directory: {dir_path}")
            created_dirs.append(directory)
    
    # If no new directories were created, log it
    if not created_dirs:
        logger.info("All directories already exist")
    
    return directories

def should_skip_file(filename):
    """Check if a file should be skipped during organization"""
    # Skip this script itself
    if filename == os.path.basename(__file__):
        return True
    
    # Skip existing directories
    if os.path.isdir(filename):
        return True
    
    # Skip hidden files
    if filename.startswith('.'):
        return True
    
    # Skip certain files
    skip_files = [
        'README.md',        # Keep README in root
        '__init__.py',      # Keep init in root
        '.gitignore'        # Keep gitignore in root
    ]
    if filename in skip_files:
        return True
    
    return False

def categorize_file(filename):
    """Determine which category a file belongs to"""
    
    # Weather-related scripts
    if any(x in filename for x in ['weather', 'climat']):
        return 'weather'
    
    # Data collection scripts
    if any(x in filename for x in ['collect', 'data_', 'devices_', 'fetch']):
        return 'data_collection'
    
    # Database-related scripts
    if any(x in filename for x in ['database', 'db_', 'sql', 'schema']):
        return 'database'
    
    # Report-generation scripts
    if any(x in filename for x in ['report', 'chart', 'graph', 'visuali']):
        return 'reports'
    
    # Notification scripts
    if any(x in filename for x in ['notif', 'alert', 'telegram', 'email']):
        return 'notifications'
    
    # Cron and scheduled scripts
    if any(x in filename for x in ['cron', 'sched', 'run_', 'task']):
        return 'cron'
    
    # Setup scripts
    if any(x in filename for x in ['setup', 'install', 'config', 'init']):
        return 'setup'
    
    # Default to utils for anything else
    return 'utils'

def organize_scripts(scripts_dir, dry_run=False):
    """Organize scripts into the appropriate subdirectories"""
    # Get a list of all files in the scripts directory
    files = [f for f in os.listdir(scripts_dir) 
             if os.path.isfile(os.path.join(scripts_dir, f)) and not should_skip_file(f)]
    
    # Sort files by name for consistent output
    files.sort()
    
    # Count of files moved to each directory
    moved_counts = {dir_name: 0 for dir_name in create_directories(scripts_dir, dry_run)}
    
    # Move each file to the appropriate directory
    for filename in files:
        src_path = os.path.join(scripts_dir, filename)
        category = categorize_file(filename)
        dst_dir = os.path.join(scripts_dir, category)
        dst_path = os.path.join(dst_dir, filename)
        
        # Check if file already exists in destination
        if os.path.exists(dst_path):
            logger.warning(f"File already exists in destination: {dst_path}")
            continue
        
        if not dry_run:
            # Make sure the directory exists
            os.makedirs(dst_dir, exist_ok=True)
            # Move the file
            shutil.move(src_path, dst_path)
            logger.info(f"Moved {filename} to {category}/")
        else:
            logger.info(f"Would move {filename} to {category}/")
        
        moved_counts[category] += 1
    
    # Log summary of files moved
    logger.info("\nSummary:")
    for dir_name, count in moved_counts.items():
        logger.info(f"{dir_name}: {count} files {'would be ' if dry_run else ''}moved")
    
    return moved_counts

def create_readme_files(scripts_dir, dry_run=False):
    """Create README.md files in each subdirectory explaining its purpose"""
    # Define the readme content for each directory
    readme_content = {
        'data_collection': """# Data Collection Scripts

This directory contains scripts for collecting data from the Growatt API.

## Scripts

- `collect_devices.py` - Collects device information
- `collect_inverter_data.py` - Collects data from inverters
- `devices_data_collector.py` - Collects data from devices
- `collect_all_data.py` - Collects all types of data
""",
        'weather': """# Weather Scripts

This directory contains scripts for collecting and processing weather data.

## Scripts

- `weather_collector.py` - Collects basic weather data
- `collect_complete_weather.py` - Collects comprehensive weather data
- `extend_weather_schema.py` - Extends the database schema for weather data
- `test_weather_api.py` - Tests the weather API endpoints
""",
        'database': """# Database Scripts

This directory contains scripts for database operations and maintenance.

## Scripts

- `db_data_collector.py` - Collects data and stores it in the database
""",
        'reports': """# Report Scripts

This directory contains scripts for generating reports from collected data.

## Scripts

- `database_report.py` - Generates database reports
- `energy_report.py` - Generates energy usage reports
""",
        'utils': """# Utility Scripts

This directory contains utility scripts used by other parts of the application.

## Scripts

- `utils.py` - Contains utility functions
- `config.py` - Configuration-related functionality
""",
        'cron': """# Cron and Scheduler Scripts

This directory contains scripts for scheduling and running tasks.

## Scripts

- `run_collectors.py` - Entry point for running collectors
- `run_data_collector.sh` - Shell script for running data collectors
- `run_weather_collector.sh` - Shell script for running weather collectors
- `crontab.example` - Example crontab configuration
""",
        'notifications': """# Notification Scripts

This directory contains scripts for sending notifications.

## Scripts

- `device_notification.py` - Sends notifications about devices
- `offline_devices_notification.py` - Sends notifications about offline devices
""",
        'setup': """# Setup Scripts

This directory contains scripts for setting up and configuring the application.

## Scripts

- `setup_notification_history.py` - Sets up notification history
- `setup_telegram_cron.py` - Sets up Telegram notifications in cron
- `create-ssl-cert.sh` - Creates SSL certificates
"""
    }
    
    # Create README.md in each subdirectory
    for dir_name, content in readme_content.items():
        readme_path = os.path.join(scripts_dir, dir_name, 'README.md')
        if not os.path.exists(readme_path):
            if not dry_run:
                os.makedirs(os.path.dirname(readme_path), exist_ok=True)
                with open(readme_path, 'w') as f:
                    f.write(content)
                logger.info(f"Created README.md in {dir_name}/")
            else:
                logger.info(f"Would create README.md in {dir_name}/")

def update_main_readme(scripts_dir, dry_run=False):
    """Update the main README.md to reflect the new directory structure"""
    readme_path = os.path.join(scripts_dir, 'README.md')
    
    new_readme_content = """# Growatt Scripts

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
# Collect all data
./cron/run_data_collector.sh

# Collect weather data
./cron/run_weather_collector.sh

# With specific options
DAYS_BACK=3 VERBOSE=true ./cron/run_data_collector.sh

# For a specific plant
PLANT_ID=10031698 ./cron/run_weather_collector.sh
```

### Scheduling

Check `cron/crontab.example` for recommended scheduling configurations.
"""
    
    if not dry_run:
        with open(readme_path, 'w') as f:
            f.write(new_readme_content)
        logger.info("Updated main README.md")
    else:
        logger.info("Would update main README.md")

def main():
    """Main function to organize scripts"""
    args = parse_arguments()
    
    # Get the path to the scripts directory
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Organizing scripts in: {scripts_dir}")
    
    # Create necessary directories
    logger.info("Creating subdirectories...")
    create_directories(scripts_dir, args.dry_run)
    
    # Organize scripts
    logger.info("Organizing scripts...")
    organize_scripts(scripts_dir, args.dry_run)
    
    # Create README files in each subdirectory
    logger.info("Creating README files...")
    create_readme_files(scripts_dir, args.dry_run)
    
    # Update main README
    logger.info("Updating main README...")
    update_main_readme(scripts_dir, args.dry_run)
    
    if args.dry_run:
        logger.info("\nThis was a dry run. No files were actually moved or created.")
    else:
        logger.info("\nScript organization complete! The scripts directory has been reorganized.")

if __name__ == "__main__":
    main() 