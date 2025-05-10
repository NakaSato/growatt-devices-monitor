#!/usr/bin/env python3
"""
Script to fix all datetime.now() calls in Growatt Devices Monitor application.
This script adds imports for timezone utilities and replaces all datetime.now() calls
with timezone-aware alternatives.
"""

import os
import re
import glob

def add_timezone_utils_import(content):
    """Add the import for timezone_utils if it's not already present"""
    if "from app.timezone_utils import" not in content:
        # Find the imports section
        if "import datetime" in content or "from datetime import" in content:
            # Add after datetime import
            content = re.sub(
                r"(from datetime .*|import datetime.*)\n",
                r"\1\n\n# Import timezone utilities\nfrom app.timezone_utils import get_now, isoformat_now, timestamp_now\n",
                content,
                count=1
            )
        else:
            # Add at the top of imports
            content = "from app.timezone_utils import get_now, isoformat_now, timestamp_now\n" + content
    return content

def fix_datetime_calls(content):
    """Replace all variations of datetime.now() calls with timezone-aware versions"""
    # Replace datetime.now().isoformat() with isoformat_now()
    content = re.sub(r"datetime\.now\(\)\.isoformat\(\)", "isoformat_now()", content)
    
    # Replace datetime.now().timestamp() with timestamp_now()
    content = re.sub(r"datetime\.now\(\)\.timestamp\(\)", "timestamp_now()", content)
    
    # Replace datetime.now().strftime(x) with format_datetime(None, x)
    content = re.sub(r"datetime\.now\(\)\.strftime\(['\"](.+)['\"]\)", r"format_datetime(None, '\1')", content)
    
    # Replace remaining datetime.now() with get_now()
    content = re.sub(r"datetime\.now\(\)", "get_now()", content)
    
    return content

def process_file(file_path):
    """Process a single file to add imports and fix datetime calls"""
    print(f"Processing {file_path}...")
    
    # Read file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if file contains datetime.now() calls
    if "datetime.now()" in content:
        # Add timezone utils import
        content = add_timezone_utils_import(content)
        
        # Fix datetime calls
        original_content = content
        content = fix_datetime_calls(content)
        
        # Write modified content if changes were made
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Updated {file_path}")
        else:
            print(f"  ⚠️ No changes needed in {file_path}")
    else:
        print(f"  ℹ️ No datetime.now() calls found in {file_path}")

def process_all_files():
    """Process all Python files in the app directory"""
    # Get the base path
    base_path = "/Users/chanthawat/Developments/py-dev/growatt-devices-monitor"
    
    # Define paths to check
    paths_to_check = [
        os.path.join(base_path, "app", "services", "*.py"),
        os.path.join(base_path, "app", "core", "*.py"),
    ]
    
    # Find all Python files in specified directories
    python_files = []
    for path_pattern in paths_to_check:
        python_files.extend(glob.glob(path_pattern))
    
    print(f"Found {len(python_files)} Python files to check")
    
    # Process each file
    for file_path in python_files:
        process_file(file_path)
    
    print("All files processed")

if __name__ == "__main__":
    process_all_files()
