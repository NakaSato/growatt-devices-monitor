#!/usr/bin/env python3
"""
Test all scheduled jobs in the Growatt Devices Monitor application.
"""
import sys
import time
from datetime import datetime
from app.services.background_service import background_service
from app.services.scheduler import get_scheduler

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, '='))
    print("=" * 80)

def test_device_status_monitor():
    """Test the device status monitor job."""
    print_header("TESTING DEVICE STATUS MONITOR")
    
    # Get the job function
    job_func = background_service._import_function(
        'app.services.device_status_tracker:check_devices_status'
    )
    
    if not job_func:
        print("❌ Failed to import device status monitor function")
        return False
    
    print("✅ Successfully imported device status monitor function")
    
    # Run the job function
    try:
        print("\nRunning device status check...")
        result = job_func()
        print(f"Result: {result}")
        print("✅ Device status check completed successfully")
        return True
    except Exception as e:
        print(f"❌ Error running device status check: {e}")
        return False

def test_device_data_collector():
    """Test the device data collector job."""
    print_header("TESTING DEVICE DATA COLLECTOR")
    
    # Get the job function
    job_func = background_service._import_function(
        'app.data_collector:collect_device_data'
    )
    
    if not job_func:
        print("❌ Failed to import device data collector function")
        return False
    
    print("✅ Successfully imported device data collector function")
    
    # Run the job function
    try:
        print("\nRunning device data collection...")
        start_time = time.time()
        result = job_func()
        duration = time.time() - start_time
        
        print(f"\nCollection completed in {duration:.2f} seconds")
        print(f"Result: {result}")
        
        # Check if the operation was successful
        if result:
            print("✅ Device data collection completed successfully")
            return True
        else:
            print("❌ Device data collection failed")
            return False
    except Exception as e:
        print(f"❌ Error running device data collection: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plant_data_collector():
    """Test the plant data collector job."""
    print_header("TESTING PLANT DATA COLLECTOR")
    
    # Get the job function
    job_func = background_service._import_function(
        'app.data_collector:collect_plant_data'
    )
    
    if not job_func:
        print("❌ Failed to import plant data collector function")
        return False
    
    print("✅ Successfully imported plant data collector function")
    
    # Run the job function
    try:
        print("\nRunning plant data collection...")
        start_time = time.time()
        result = job_func()
        duration = time.time() - start_time
        
        print(f"\nCollection completed in {duration:.2f} seconds")
        print(f"Result: {result.get('success', False)}")
        
        if 'results' in result:
            print("\nResults:")
            print(f"- Plants processed: {result['results'].get('plants', 0)}")
            
            if 'errors' in result['results'] and result['results']['errors']:
                print("\nErrors:")
                for error in result['results']['errors'][:3]:  # Show first 3 errors
                    print(f"- {error}")
                if len(result['results']['errors']) > 3:
                    print(f"- ... and {len(result['results']['errors']) - 3} more errors")
        
        print("✅ Plant data collection completed")
        return result.get('success', False)
    except Exception as e:
        print(f"❌ Error running plant data collection: {e}")
        return False

def test_offline_notifications():
    """Test the offline notifications job."""
    print_header("TESTING OFFLINE NOTIFICATIONS")
    
    # Import the NotificationService class
    try:
        from app.services.notification_service import NotificationService
        notification_service = NotificationService()
        print("✅ Successfully imported NotificationService")
    except Exception as e:
        print(f"❌ Failed to import NotificationService: {e}")
        return False
    
    # Create a test device data dictionary
    test_device = {
        'serial_number': 'TEST123',
        'alias': 'Test Device',
        'plant_id': '12345',
        'plant_name': 'Test Plant',
        'status': 'offline',
        'last_update_time': '2025-05-08 10:00:00'
    }
    
    # Test sending a notification
    try:
        print("\nSending test offline notification...")
        result = notification_service.send_device_offline_notification(test_device)
        print(f"Notification sent: {result}")
        
        # Test cooldown functionality
        print("\nTesting notification cooldown...")
        result_cooldown = notification_service.send_device_offline_notification(test_device)
        print(f"Second notification within cooldown: {'skipped' if not result_cooldown else 'sent (unexpected)'}")
        
        print("✅ Offline notifications test completed")
        return True
    except Exception as e:
        print(f"❌ Error testing offline notifications: {e}")
        return False

def test_all_jobs():
    """Test all scheduled jobs."""
    print_header("STARTING SCHEDULED JOBS TEST")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'device_status': test_device_status_monitor(),
        'device_data': test_device_data_collector(),
        'plant_data': test_plant_data_collector(),
        'offline_notifications': test_offline_notifications()
    }
    
    # Print summary
    print_header("TEST SUMMARY")
    success = all(results.values())
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name.replace('_', ' ').title()}: {status}")
    
    if success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n⚠️  Some tests failed. Please check the logs above for details.")
    
    return success

if __name__ == "__main__":
    # Initialize the background service if needed
    from app import create_app
    app = create_app()
    
    # Run the tests
    success = test_all_jobs()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
