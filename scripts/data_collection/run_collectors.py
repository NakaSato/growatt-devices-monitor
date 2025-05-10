#!/usr/bin/env python3
"""
Run Collectors Script

This script provides a unified entry point to run various data collectors.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Import common utilities
from script import configure_script_logging
from script.utils import (
    ensure_dir,
    create_common_parser,
    add_date_range_args,
    parse_date_range
)

# Import collectors
from script.collectors.collect_devices import DevicesCollector
# These will be imported in future when refactored
# from script.collectors.collect_inverter_data import InverterDataCollector
# from script.collectors.collect_all_data import AllDataCollector

# Configure logging
logger = configure_script_logging("run_collectors")

def run_devices_collector(args):
    """
    Run the devices collector
    
    Args:
        args: Command line arguments
        
    Returns:
        int: Exit code
    """
    # Ensure output directory exists
    output_dir = ensure_dir(args.output_dir)
    
    # Set default output file if not provided
    if not args.output_file:
        output_file = os.path.join(output_dir, f"devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    else:
        output_file = args.output_file
    
    logger.info(f"Starting device data collection from {args.server_url}")
    
    # Initialize collector
    collector = DevicesCollector(
        base_url=args.server_url,
        username=args.username,
        password=args.password
    )
    
    # Run collection
    result = collector.run(output_file)
    
    if result:
        logger.info(f"Device data collection completed successfully: {output_file}")
        print(f"SUCCESS: {output_file}")
        return 0
    else:
        logger.error("Device data collection failed")
        print("ERROR: Device data collection failed")
        return 1

# More collector functions will be added later
# def run_inverter_collector(args):
#     ...
# 
# def run_all_collector(args):
#     ...

def main():
    """Main function"""
    # Create parser with common arguments
    parser = create_common_parser()
    parser.description = "Run various Growatt data collectors"
    
    # Add subparsers for different collector types
    subparsers = parser.add_subparsers(dest="collector_type", help="Type of collector to run")
    
    # Devices collector subparser
    devices_parser = subparsers.add_parser("devices", help="Collect device data")
    devices_parser.add_argument("--output", dest="output_file", help="Output JSON file path")
    
    # Inverter data collector subparser
    inverter_parser = subparsers.add_parser("inverter", help="Collect inverter data")
    add_date_range_args(inverter_parser)
    
    # All data collector subparser
    all_parser = subparsers.add_parser("all", help="Collect all data")
    add_date_range_args(all_parser)
    all_parser.add_argument("--weather", dest="include_weather", action="store_true", 
                           help="Include weather data")
    all_parser.add_argument("--save-files", dest="save_to_file", action="store_true",
                           help="Save raw data to JSON files")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Run appropriate collector
    if args.collector_type == "devices":
        return run_devices_collector(args)
    elif args.collector_type == "inverter":
        logger.error("Inverter data collector not yet implemented in this script")
        return 1
        # return run_inverter_collector(args)
    elif args.collector_type == "all":
        logger.error("All data collector not yet implemented in this script")
        return 1
        # return run_all_collector(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 