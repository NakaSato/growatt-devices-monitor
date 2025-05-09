#!/usr/bin/env python3
"""
Script to replace all occurrences of datetime.now() with timezone-aware
datetime.now(get_timezone()) throughout app/data_collector.py
"""

import re
import os

def fix_datetime_now_calls(file_path):
    """
    Replace all datetime.now() calls with timezone-aware version
    """
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace datetime.now() with datetime.now(get_timezone())
    pattern = r'datetime\.now\(\)'
    replacement = 'datetime.now(get_timezone())'
    
    # Count occurrences and replace
    count = len(re.findall(pattern, content))
    modified_content = re.sub(pattern, replacement, content)
    
    # Write the modified content back to the file
    with open(file_path, 'w') as f:
        f.write(modified_content)
    
    print(f"Replaced {count} occurrences of datetime.now() in {file_path}")

if __name__ == "__main__":
    # Path to the file
    data_collector_path = os.path.join("app", "data_collector.py")
    if not os.path.exists(data_collector_path):
        # Try with full path
        data_collector_path = "/Users/chanthawat/Developments/py-dev/growatt-devices-monitor/app/data_collector.py"
    
    if os.path.exists(data_collector_path):
        fix_datetime_now_calls(data_collector_path)
    else:
        print(f"Error: Could not find {data_collector_path}")
