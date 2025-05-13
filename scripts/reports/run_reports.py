#!/usr/bin/env python3
"""
Report Generator Script

This script provides a unified interface to generate different types of reports.

Usage:
    python run_reports.py [report_type] [options]
    
Report Types:
    database - Generate database reports with device status and energy data
    energy   - Generate energy production reports
    
Example:
    python run_reports.py database --days 30 --email user@example.com
    python run_reports.py energy --weekly --telegram
"""

import os
import sys
import logging
import argparse
import importlib
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path to make script module importable
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Configure logging
def configure_script_logging(name, level=logging.INFO):
    """Configure logging for scripts with console and file output"""
    # Ensure logs directory exists
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicate logs
    if logger.handlers:
        logger.handlers.clear()
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(os.path.join(logs_dir, f'{name}.log'))
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Import common utilities
from scripts.utils import (
    create_common_parser,
    add_date_range_args,
    parse_date_range
)

# Configure logging
logger = configure_script_logging("run_reports")

def run_database_report(args):
    """
    Run the database report generator
    
    Args:
        args: Command line arguments
        
    Returns:
        int: Exit code
    """
    try:
        # Try to import the improved database report module
        try:
            from scripts.reports.improved_database_report import main as db_report_main
            logger.info("Using improved database report generator")
        except ImportError:
            # Fall back to the original database report module
            from scripts.reports.database_report import main as db_report_main
            logger.info("Using original database report generator")
        
        # Run the report generator
        result = db_report_main()
        return result
    except ImportError:
        logger.error("Failed to import database report module")
        return 1
    except Exception as e:
        logger.error(f"Error running database report: {e}")
        return 1

def run_energy_report(args):
    """
    Run the energy report generator
    
    Args:
        args: Command line arguments
        
    Returns:
        int: Exit code
    """
    try:
        from script.reports.energy_report import main as energy_report_main
        
        # Modify sys.argv to pass the correct arguments
        orig_argv = sys.argv
        
        # Build new argv list
        new_argv = [orig_argv[0]]
        
        # Add timeframe
        if args.timeframe == 'daily':
            new_argv.append('--daily')
        elif args.timeframe == 'weekly':
            new_argv.append('--weekly')
        elif args.timeframe == 'monthly':
            new_argv.append('--monthly')
        
        # Add telegram flag if specified
        if args.telegram:
            new_argv.append('--telegram')
        
        # Add debug flag if verbose
        if args.verbose:
            new_argv.append('--debug')
        
        # Replace sys.argv temporarily
        sys.argv = new_argv
        
        # Run the report generator
        result = energy_report_main()
        
        # Restore original sys.argv
        sys.argv = orig_argv
        
        return result
    except ImportError:
        logger.error("Failed to import energy report module")
        return 1
    except Exception as e:
        logger.error(f"Error running energy report: {e}")
        return 1

def validate_args(args):
    """
    Validate command line arguments
    
    Args:
        args: Command line arguments
        
    Returns:
        bool: True if arguments are valid, False otherwise
    """
    if not args.report_type:
        logger.error("No report type specified")
        return False
        
    if args.report_type == 'energy' and not args.timeframe:
        logger.error("No timeframe specified for energy report")
        return False
        
    return True

def main():
    """Main function"""
    # Create parser with common arguments
    parser = create_common_parser()
    parser.description = "Generate reports from Growatt device data"
    
    # Add subparsers for different report types
    subparsers = parser.add_subparsers(dest="report_type", help="Type of report to generate")
    
    # Database report subparser
    db_parser = subparsers.add_parser("database", help="Generate database reports")
    add_date_range_args(db_parser)
    db_parser.add_argument("--email", dest="email", help="Email address to send the report to")
    db_parser.add_argument("--output", dest="output_file", help="Output file path for the PDF report")
    
    # Energy report subparser
    energy_parser = subparsers.add_parser("energy", help="Generate energy production reports")
    energy_parser.add_argument("--telegram", dest="telegram", action="store_true",
                             help="Send report via Telegram")
    
    # Add daily/weekly/monthly as direct arguments for convenience
    energy_group = energy_parser.add_mutually_exclusive_group(required=True)
    energy_group.add_argument("--daily", dest="daily", action="store_true",
                             help="Generate daily energy report (last 24 hours)")
    energy_group.add_argument("--weekly", dest="weekly", action="store_true",
                             help="Generate weekly energy report (last 7 days)")
    energy_group.add_argument("--monthly", dest="monthly", action="store_true",
                             help="Generate monthly energy report (last 30 days)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Convert daily/weekly/monthly flags to timeframe
    if hasattr(args, 'daily') and args.daily:
        args.timeframe = 'daily'
    elif hasattr(args, 'weekly') and args.weekly:
        args.timeframe = 'weekly'
    elif hasattr(args, 'monthly') and args.monthly:
        args.timeframe = 'monthly'
    
    # Validate arguments
    if not validate_args(args):
        parser.print_help()
        return 1
    
    # Run appropriate report generator
    if args.report_type == "database":
        return run_database_report(args)
    elif args.report_type == "energy":
        return run_energy_report(args)
    else:
        logger.error(f"Unknown report type: {args.report_type}")
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 