#!/usr/bin/env python3
"""
Utilities for Growatt Devices Monitor Scripts

This module provides common utility functions for scripts.
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Import from the package's __init__.py
from script import configure_script_logging

def ensure_dir(directory: str) -> str:
    """
    Ensure directory exists, create if not
    
    Args:
        directory: Directory path to ensure
        
    Returns:
        str: Path to the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")
    return directory

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string (e.g., "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def safe_json_serialize(obj: Any) -> Any:
    """
    Convert objects to JSON-serializable format
    
    Args:
        obj: Object to serialize
        
    Returns:
        Any: Serializable version of the object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (list, tuple)):
        return [safe_json_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    return obj

def save_to_json(data: Any, filename: str, pretty: bool = True) -> bool:
    """
    Save data to JSON file
    
    Args:
        data: Data to save
        filename: Path to output file
        pretty: Whether to format JSON with indentation
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Convert data to JSON-serializable format
        json_data = safe_json_serialize(data)
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(json_data, f, ensure_ascii=False)
        
        logging.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error saving data to {filename}: {str(e)}")
        return False

def load_from_json(filename: str) -> Any:
    """
    Load data from JSON file
    
    Args:
        filename: Path to JSON file
        
    Returns:
        Any: Loaded data
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading data from {filename}: {str(e)}")
        return None

def retry_with_backoff(func, retries: int = 3, backoff_factor: int = 2):
    """
    Decorator for retrying a function with exponential backoff
    
    Args:
        func: Function to retry
        retries: Maximum number of retries
        backoff_factor: Base factor for exponential backoff
        
    Returns:
        Wrapped function with retry logic
    """
    def wrapper(*args, **kwargs):
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == retries - 1:
                    # Last attempt failed, re-raise exception
                    raise
                
                # Log error and wait before retry
                logging.warning(f"Attempt {attempt+1}/{retries} failed: {str(e)}")
                wait_time = backoff_factor ** attempt
                logging.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    return wrapper

def create_common_parser() -> argparse.ArgumentParser:
    """
    Create a common argument parser with standard options
    
    Returns:
        argparse.ArgumentParser: Configured parser
    """
    parser = argparse.ArgumentParser(description="Growatt Devices Monitor Script")
    
    # Common arguments
    parser.add_argument("--server", dest="server_url", default="http://localhost:8000", 
                        help="URL of the server running the Growatt monitor")
    parser.add_argument("--username", dest="username", help="Growatt API username")
    parser.add_argument("--password", dest="password", help="Growatt API password")
    parser.add_argument("--verbose", dest="verbose", action="store_true", 
                        help="Enable verbose logging")
    parser.add_argument("--output-dir", dest="output_dir", default="data",
                        help="Directory for output files")
    
    return parser

def add_date_range_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add date range arguments to a parser
    
    Args:
        parser: Argument parser to modify
        
    Returns:
        argparse.ArgumentParser: Modified parser
    """
    parser.add_argument("--days", dest="days_back", type=int, default=7,
                        help="Number of days of historical data to collect")
    parser.add_argument("--start-date", dest="start_date", 
                        help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", dest="end_date",
                        help="End date in YYYY-MM-DD format")
    
    return parser

def parse_date_range(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Parse date range from arguments
    
    Args:
        args: Parsed arguments
        
    Returns:
        dict: Dictionary with parsed date range
    """
    date_range = {}
    
    if args.start_date:
        try:
            date_range['start_date'] = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            logging.error(f"Invalid start date format: {args.start_date}")
    
    if args.end_date:
        try:
            date_range['end_date'] = datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            logging.error(f"Invalid end date format: {args.end_date}")
    
    if not (args.start_date or args.end_date) and args.days_back:
        date_range['days_back'] = args.days_back
    
    return date_range

def make_api_request(url: str, method: str = "GET", data: Dict = None, 
                     timeout: int = 60, retries: int = 3) -> Dict:
    """
    Make an API request with retries
    
    Args:
        url: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        data: Data to send with request
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        
    Returns:
        dict: Response data or error information
    """
    @retry_with_backoff(retries=retries)
    def _make_request():
        response = requests.request(
            method=method.upper(),
            url=url,
            json=data if method.upper() in ["POST", "PUT", "PATCH"] else None,
            params=data if method.upper() == "GET" else None,
            timeout=timeout
        )
        
        response.raise_for_status()
        
        if response.headers.get('content-type', '').startswith('application/json'):
            return response.json()
        return {"success": True, "data": response.text}
    
    try:
        return _make_request()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error: {str(e)}")
        try:
            return {"success": False, "error": e.response.json(), "status_code": e.response.status_code}
        except (ValueError, AttributeError):
            return {"success": False, "error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    except Exception as e:
        logging.error(f"Request error: {str(e)}")
        return {"success": False, "error": str(e)} 