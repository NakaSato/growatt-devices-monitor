#!/usr/bin/env python3
"""
Test script for the get_weather function from the Growatt API

This script directly calls the get_weather function from the Growatt class
to test API connectivity and data retrieval.

Usage:
    python test_weather_api.py [plant_id]

If no plant_id is specified, the script will get the list of plants and
use the first plant ID.
"""

import os
import sys
import json
import argparse

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Growatt class
from app.core.growatt import Growatt
from app.config import Config

def parse_arguments():
    parser = argparse.ArgumentParser(description='Test the get_weather function from Growatt API')
    parser.add_argument('plant_id', nargs='?', help='Optional plant ID to test with. If not provided, the first plant will be used.')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Check if credentials are configured
    if not Config.GROWATT_USERNAME or not Config.GROWATT_PASSWORD:
        print("Growatt API credentials not configured. Please set GROWATT_USERNAME and GROWATT_PASSWORD environment variables.")
        sys.exit(1)
    
    # Initialize Growatt API
    print(f"Initializing Growatt API with username: {Config.GROWATT_USERNAME}")
    api = Growatt()
    
    # Login to Growatt API
    print("Logging in to Growatt API...")
    login_success = api.login(Config.GROWATT_USERNAME, Config.GROWATT_PASSWORD)
    
    if not login_success:
        print("Failed to login to Growatt API")
        sys.exit(1)
    
    print("Successfully logged in to Growatt API")
    
    # Get plant ID if not provided
    plant_id = args.plant_id
    if not plant_id:
        print("No plant ID provided, getting list of plants...")
        plants = api.get_plants()
        if not plants:
            print("No plants found")
            sys.exit(1)
        
        plant_id = plants[0]['id']
        plant_name = plants[0]['plantName']
        print(f"Using first plant: {plant_name} (ID: {plant_id})")
    
    # Get weather data
    print(f"Getting weather data for plant ID: {plant_id}")
    try:
        weather_data = api.get_weather(plant_id)
        
        # Pretty print the JSON response
        print("\nWeather Data Response:")
        print(json.dumps(weather_data, indent=2))
        
        # Extract and show specific fields
        if 'datas' in weather_data and weather_data['datas']:
            device_data = weather_data['datas'][0]
            print("\nExtracted Weather Information:")
            print(f"Temperature: {device_data.get('envTemp', 'N/A')}°C")
            print(f"Humidity: {device_data.get('envHumidity', 'N/A')}%")
            print(f"Wind Speed: {device_data.get('windSpeed', 'N/A')} m/s")
            print(f"Wind Angle: {device_data.get('windAngle', 'N/A')}°")
            print(f"Panel Temperature: {device_data.get('panelTemp', 'N/A')}°C")
            print(f"Last Update: {device_data.get('lastUpdateTime', 'N/A')}")
            print(f"Device Status: {device_data.get('deviceStatus', 'N/A')}")
        else:
            print("No weather device data found in the response")
    
    except Exception as e:
        print(f"Error getting weather data: {str(e)}")
        sys.exit(1)
    
    # Logout from API
    print("\nLogging out from Growatt API...")
    api.logout()
    print("Successfully logged out")

if __name__ == "__main__":
    main() 