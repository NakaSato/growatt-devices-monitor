#!/usr/bin/env python3
"""
Test script for the Growatt API integration.
This script demonstrates how to use the Growatt class to interact with the Growatt API.

Usage:
    python test_growatt_api.py

Environment variables:
    GROWATT_USERNAME: Your Growatt username
    GROWATT_PASSWORD: Your Growatt password
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.growatt import Growatt

def test_get_device_list():
    """Test specifically the get_device_list functionality."""
    # Get credentials from environment variables
    username = os.environ.get('GROWATT_USERNAME')
    password = os.environ.get('GROWATT_PASSWORD')
    
    if not username or not password:
        print("Error: Please set GROWATT_USERNAME and GROWATT_PASSWORD environment variables.")
        return 1
    
    # Create Growatt API client instance
    growatt = Growatt()
    
    try:
        # Login
        print(f"Logging in with username: {username}")
        login_success = growatt.login(username, password)
        
        if not login_success:
            print("Login failed. Please check your credentials.")
            return 1
        
        print("Login successful!")
        
        # Get plants
        print("\nFetching plants...")
        plants = growatt.get_plants()
        
        if not plants:
            print("No plants found for this account.")
            return 1
        
        print(f"Found {len(plants)} plants")
        
        # For each plant, test the get_device_list method
        for plant in plants:
            plant_id = plant.get('id')
            plant_name = plant.get('plantName', 'Unnamed plant')
            
            print(f"\nTesting get_device_list for plant: {plant_name} (ID: {plant_id})")
            
            # Get devices for this plant using get_device_list
            devices_response = growatt.get_device_list(plant_id)
            
            # Print the full response for debugging
            print(f"Full response data for plant {plant_id}:")
            print(json.dumps(devices_response, indent=2))
            print("=" * 80)  # Separator for better readability
            
            # Check response structure and print results
            if devices_response and 'obj' in devices_response and 'datas' in devices_response['obj']:
                device_list = devices_response['obj']['datas']
                total_count = devices_response['obj'].get('totalCount', len(device_list))
                
                print(f"Successfully retrieved {len(device_list)} devices (totalCount: {total_count})")
                
                # Print some details about the first few devices (limit to 5 for brevity)
                for i, device in enumerate(device_list[:5], 1):
                    device_sn = device.get('deviceSn', 'Unknown SN')
                    device_type = device.get('deviceType', 'Unknown type')
                    device_name = device.get('deviceName', device_sn)
                    device_status = device.get('status', 'Unknown status')
                    
                    print(f"  Device {i}: {device_name} (Type: {device_type}, SN: {device_sn}, Status: {device_status})")
                
                # If there are more than 5 devices, indicate there are more
                if len(device_list) > 5:
                    print(f"  ... and {len(device_list) - 5} more devices")
            else:
                print("No devices found or unexpected response format.")
                print(f"Response structure: {json.dumps(devices_response, indent=2)[:200]}...")
        
        print("\nDevice list testing completed successfully!")
        return 0

    except Exception as e:
        print(f"Error during get_device_list testing: {str(e)}")
        return 1
    finally:
        # Always try to logout
        if hasattr(growatt, 'is_logged_in') and growatt.is_logged_in:
            print("\nLogging out...")
            growatt.logout()

def main():
    """Test the Growatt API functionality."""
    # Get credentials from environment variables
    username = os.environ.get('GROWATT_USERNAME')
    password = os.environ.get('GROWATT_PASSWORD')
    
    if not username or not password:
        print("Error: Please set GROWATT_USERNAME and GROWATT_PASSWORD environment variables.")
        print("Example:")
        print("  export GROWATT_USERNAME='your_username'")
        print("  export GROWATT_PASSWORD='your_password'")
        return 1
    
    # Create Growatt API client instance
    growatt = Growatt()
    
    try:
        # Test login
        print(f"Attempting to login with username: {username}")
        login_success = growatt.login(username, password)
        
        if not login_success:
            print("Login failed. Please check your credentials.")
            return 1
        
        print("Login successful!")
        
        # Get and print plants
        print("\nFetching plants...")
        plants = growatt.get_plants()
        
        if not plants:
            print("No plants found for this account.")
            return 1
        
        print(f"Found {len(plants)} plants:")
        for i, plant in enumerate(plants, 1):
            plant_id = plant.get('id')
            plant_name = plant.get('plantName', 'Unnamed plant')
            print(f"  {i}. Plant ID: {plant_id}, Name: {plant_name}")
        
        # Let's get details for the first plant
        if plants:
            first_plant_id = plants[0].get('id')
            first_plant_name = plants[0].get('plantName', 'Unnamed plant')
            
            print(f"\nFetching details for plant: {first_plant_name} (ID: {first_plant_id})...")
            plant_details = growatt.get_plant(first_plant_id)
            
            print(f"Plant location: {plant_details.get('city', 'Unknown')}, "
                  f"Nominal power: {plant_details.get('nominalPower', 'Unknown')} W")
            
            # Get devices for this plant
            print(f"\nFetching devices for plant {first_plant_name}...")
            devices = growatt.get_device_list(first_plant_id)
            
            if devices and 'obj' in devices and 'datas' in devices['obj']:
                device_list = devices['obj']['datas']
                print(f"Found {len(device_list)} devices:")
                
                for i, device in enumerate(device_list, 1):
                    device_sn = device.get('deviceSn', 'Unknown SN')
                    device_type = device.get('deviceType', 'Unknown type')
                    device_name = device.get('deviceName', 'Unnamed device')
                    
                    print(f"  {i}. Device: {device_name}, Type: {device_type}, SN: {device_sn}")
            else:
                print("No devices found or unexpected response format.")
            
            # Test fault logs retrieval
            print(f"\nFetching fault logs for plant {first_plant_name}...")
            today = datetime.now().strftime("%Y-%m-%d")
            fault_logs = growatt.get_fault_logs(first_plant_id, date=today)
            
            if fault_logs and 'obj' in fault_logs and 'datas' in fault_logs['obj']:
                logs = fault_logs['obj']['datas']
                if logs:
                    print(f"Found {len(logs)} fault logs for today:")
                    for i, log in enumerate(logs[:5], 1):  # Show first 5 logs
                        print(f"  {i}. Device: {log.get('deviceName', 'Unknown')}, "
                              f"Error: {log.get('errorMsg', 'No message')}, "
                              f"Time: {log.get('happenTime', 'Unknown')}")
                else:
                    print("No fault logs found for today (good news!).")
            else:
                print("No fault logs found or unexpected response format.")
        
        print("\nTests completed successfully!")
        return 0

    except Exception as e:
        print(f"Error during API testing: {str(e)}")
        return 1
    finally:
        # Always try to logout
        if hasattr(growatt, 'is_logged_in') and growatt.is_logged_in:
            print("\nLogging out...")
            growatt.logout()

if __name__ == "__main__":
    # Choose which test to run
    if len(sys.argv) > 1 and sys.argv[1] == "--test-device-list":
        sys.exit(test_get_device_list())
    else:
        sys.exit(main())