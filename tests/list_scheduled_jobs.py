#!/usr/bin/env python3
"""
List all scheduled jobs in the Growatt Devices Monitor application.
"""
import os
import sys
from app import create_app

# Create the Flask application
app = create_app()

# Get the background service
background_service = app.background_service

# List all jobs
print("\n=== Scheduled Jobs ===")
jobs = background_service.get_jobs()
if not jobs:
    print("No scheduled jobs found.")
else:
    for job in jobs:
        print(f"\nJob ID: {job['id']}")
        print(f"Name: {job['name']}")
        print(f"Type: {job['type']}")
        print(f"Description: {job['description']}")
        print(f"Next Run: {job['next_run']}")
        print(f"Active: {job['active']}")
        if 'config' in job and job['config']:
            print("Configuration:")
            for key, value in job['config'].items():
                print(f"  {key}: {value}")

print("\n=== End of Job List ===\n")
