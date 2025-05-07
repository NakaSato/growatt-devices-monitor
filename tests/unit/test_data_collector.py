#!/usr/bin/env python3
"""
Test file for GrowattDataCollector in app/data_collector.py
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import json
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the class we're testing
from app.data_collector import GrowattDataCollector, collect_device_data, collect_plant_data


class TestGrowattDataCollector(unittest.TestCase):
    """Tests for the GrowattDataCollector class"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create a collector instance with mocked config
        with patch('app.data_collector.Config') as mock_config:
            # Configure mock config
            mock_config.GROWATT_USERNAME = "test-username"
            mock_config.GROWATT_PASSWORD = "test-password"
            
            # Mock the database connector and Growatt API client
            with patch('app.data_collector.DatabaseConnector') as mock_db, \
                 patch('app.data_collector.Growatt') as mock_api, \
                 patch('app.data_collector.DeviceStatusTracker') as mock_tracker:
                
                # Create mock instances
                self.mock_db_instance = MagicMock()
                mock_db.return_value = self.mock_db_instance
                
                self.mock_api_instance = MagicMock()
                mock_api.return_value = self.mock_api_instance
                
                self.mock_tracker_instance = MagicMock()
                mock_tracker.return_value = self.mock_tracker_instance
                
                # Create collector instance
                self.collector = GrowattDataCollector()
        
        # Sample data for tests
        self.sample_plants = [
            {
                "id": "PLANT001",
                "name": "Test Plant 1",
                "status": "normal",
                "capacity": 10.5,
                "location": "Test Location 1",
                "latitude": "12.345",
                "longitude": "67.890"
            },
            {
                "id": "PLANT002",
                "name": "Test Plant 2",
                "status": "fault",
                "capacity": 5.2,
                "location": "Test Location 2",
                "latitude": "23.456",
                "longitude": "78.901"
            }
        ]
        
        self.sample_devices = [
            {
                "sn": "DEVICE001",
                "alias": "Inverter 1",
                "status": "normal",
                "deviceTypeName": "Inverter",
                "lastUpdateTime": "2025-05-07 08:00:00"
            },
            {
                "sn": "DEVICE002",
                "alias": "Inverter 2",
                "status": "offline",
                "deviceTypeName": "Inverter",
                "lastUpdateTime": "2025-05-07 07:00:00"
            }
        ]
        
        self.sample_energy_data = {
            "data": [
                {
                    "date": "2025-05-01",
                    "energy": 12.34,
                    "peak_power": 3.45
                },
                {
                    "date": "2025-05-02",
                    "energy": 23.45,
                    "peak_power": 4.56
                }
            ]
        }
        
        self.sample_weather_data = {
            "temperature": "25.6",
            "weather": "Sunny",
            "humidity": "45%"
        }

    def test_init(self):
        """Test the initialization of the collector"""
        self.assertEqual(self.collector.username, "test-username")
        self.assertEqual(self.collector.password, "test-password")
        self.assertFalse(self.collector.authenticated)
        self.assertEqual(self.collector.retry_count, 3)
        self.assertEqual(self.collector.retry_delay, 2)
        self.assertFalse(self.collector.collect_json)
        self.assertEqual(self.collector.json_data, [])

    def test_enable_json_collection(self):
        """Test enabling JSON data collection"""
        # Verify initial state
        self.assertFalse(self.collector.collect_json)
        self.assertEqual(self.collector.json_data, [])
        
        # Enable JSON collection
        self.collector.enable_json_collection()
        
        # Verify new state
        self.assertTrue(self.collector.collect_json)
        self.assertEqual(self.collector.json_data, [])

    def test_add_json_data(self):
        """Test adding JSON data to the collection"""
        # Enable JSON collection
        self.collector.enable_json_collection()
        
        # Add data
        test_data = {"test": "data"}
        self.collector._add_json_data("test_type", test_data, "plant123", "device456", "test_source")
        
        # Verify data was added
        self.assertEqual(len(self.collector.json_data), 1)
        added_data = self.collector.json_data[0]
        self.assertEqual(added_data["type"], "test_type")
        self.assertEqual(json.loads(added_data["content"]), test_data)
        self.assertEqual(added_data["plant_id"], "plant123")
        self.assertEqual(added_data["device_sn"], "device456")
        self.assertEqual(added_data["source"], "test_source")

    def test_add_json_data_disabled(self):
        """Test adding JSON data when collection is disabled"""
        # Ensure JSON collection is disabled
        self.collector.collect_json = False
        
        # Add data
        self.collector._add_json_data("test_type", {"test": "data"})
        
        # Verify no data was added
        self.assertEqual(self.collector.json_data, [])

    @patch('app.data_collector.logger')
    def test_add_json_data_error(self, mock_logger):
        """Test error handling when adding JSON data"""
        # Enable JSON collection
        self.collector.enable_json_collection()
        
        # Add data that can't be serialized (e.g., circular reference)
        circular_ref = {}
        circular_ref["self"] = circular_ref
        
        # This should not raise an exception
        self.collector._add_json_data("test_type", circular_ref)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()

    def test_authenticate_success(self):
        """Test successful authentication"""
        # Configure mock API
        self.mock_api_instance.login.return_value = True
        
        # Call authenticate
        result = self.collector.authenticate()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.collector.authenticated)
        self.mock_api_instance.login.assert_called_once_with(
            username="test-username", 
            password="test-password"
        )

    def test_authenticate_failure(self):
        """Test authentication failure"""
        # Configure mock API
        self.mock_api_instance.login.return_value = False
        
        # Call authenticate
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.authenticated)
        self.mock_api_instance.login.assert_called_once()

    def test_authenticate_retry(self):
        """Test authentication with retry"""
        # Configure mock API to fail twice then succeed
        self.mock_api_instance.login.side_effect = [False, False, True]
        
        # Call authenticate
        result = self.collector.authenticate()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.collector.authenticated)
        self.assertEqual(self.mock_api_instance.login.call_count, 3)

    def test_authenticate_missing_credentials(self):
        """Test authentication with missing credentials"""
        # Set username to None
        self.collector.username = None
        
        # Call authenticate
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.authenticated)
        self.mock_api_instance.login.assert_not_called()
        
        # Reset username and set password to None
        self.collector.username = "test-username"
        self.collector.password = None
        
        # Call authenticate
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.authenticated)
        self.mock_api_instance.login.assert_not_called()

    @patch('time.sleep')
    def test_safe_api_call_success(self, mock_sleep):
        """Test successful API call via _safe_api_call"""
        # Create a mock function that returns successfully
        mock_func = MagicMock()
        mock_func.__name__ = "test_api_function"
        mock_func.return_value = {"result": "success"}
        
        # Call _safe_api_call
        result = self.collector._safe_api_call(mock_func, "arg1", "arg2", kwarg1="val1")
        
        # Verify results
        self.assertEqual(result, {"result": "success"})
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="val1")
        mock_sleep.assert_not_called()  # Sleep not called on success

    @patch('time.sleep')
    def test_safe_api_call_retry(self, mock_sleep):
        """Test API call retry via _safe_api_call"""
        # Create a mock function that fails then succeeds
        mock_func = MagicMock()
        mock_func.__name__ = "test_api_function"
        mock_func.side_effect = [Exception("API error"), {"result": "success"}]
        
        # Call _safe_api_call
        result = self.collector._safe_api_call(mock_func)
        
        # Verify results
        self.assertEqual(result, {"result": "success"})
        self.assertEqual(mock_func.call_count, 2)
        mock_sleep.assert_called_once()  # Sleep called once for retry

    @patch('time.sleep')
    def test_safe_api_call_max_retries(self, mock_sleep):
        """Test API call with max retries exhausted"""
        # Create a mock function that always fails
        mock_func = MagicMock()
        mock_func.__name__ = "test_api_function"
        mock_func.side_effect = Exception("API error")
        
        # Call _safe_api_call
        result = self.collector._safe_api_call(mock_func)
        
        # Verify results
        self.assertIsNone(result)
        self.assertEqual(mock_func.call_count, 3)  # Called retry_count times
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep called (retry_count-1) times

    @patch('time.sleep')
    def test_safe_api_call_error_response(self, mock_sleep):
        """Test API call with error in response"""
        # Create a mock function that returns an error response
        mock_func = MagicMock()
        mock_func.__name__ = "test_api_function"
        mock_func.return_value = {"error": "Access denied", "result": False}
        
        # Call _safe_api_call
        result = self.collector._safe_api_call(mock_func)
        
        # Verify results
        self.assertEqual(result, {"error": "Access denied", "result": False})
        mock_func.assert_called_once()
        mock_sleep.assert_not_called()  # No retry for API error responses

    @patch('time.sleep')
    def test_safe_api_call_reauth(self, mock_sleep):
        """Test API call with session expiry and re-authentication"""
        # Configure mock API login to succeed
        self.mock_api_instance.login.return_value = True
        
        # Create a mock function that returns session expired then succeeds
        mock_func = MagicMock()
        mock_func.__name__ = "test_api_function"
        mock_func.side_effect = [
            {"error": True, "msg": "Session expired, please login again"},
            {"result": "success"}
        ]
        
        # Set authenticated to true initially
        self.collector.authenticated = True
        
        # Call _safe_api_call
        result = self.collector._safe_api_call(mock_func)
        
        # Verify results
        self.assertEqual(result, {"result": "success"})
        self.assertEqual(mock_func.call_count, 2)  # Called twice
        self.mock_api_instance.login.assert_called_once()  # Re-authenticated once

    def test_collect_and_store_all_data_success(self):
        """Test successful data collection and storage"""
        # Configure mocks for a successful collection
        self.collector.authenticated = True  # Already authenticated
        
        # Configure API mock returns
        self.mock_api_instance.get_plants.return_value = self.sample_plants
        self.mock_api_instance.get_device_list.return_value = self.sample_devices
        self.mock_api_instance.get_energy_stats.return_value = self.sample_energy_data
        self.mock_api_instance.get_weather.return_value = self.sample_weather_data
        
        # Configure DB mock returns
        self.mock_db_instance.save_plant_data.return_value = True
        self.mock_db_instance.save_device_data.return_value = True
        self.mock_db_instance.save_energy_data_batch.return_value = 2
        self.mock_db_instance.save_weather_data.return_value = True
        
        # Configure tracker mock
        self.mock_tracker_instance.check_and_notify_status_changes.return_value = {
            'offline': 1,
            'online': 0
        }
        
        # Call collect_and_store_all_data
        result = self.collector.collect_and_store_all_data(days_back=3, include_weather=True)
        
        # Verify results
        self.assertTrue(result["success"])
        self.assertEqual(result["results"]["plants"], 2)
        self.assertEqual(result["results"]["devices"], 2)
        self.assertEqual(result["results"]["energy_stats"], 4)  # 2 devices * 2 data points
        self.assertEqual(result["results"]["weather"], 2)  # 2 plants
        self.assertEqual(len(result["results"]["errors"]), 0)
        
        # Verify API calls
        self.mock_api_instance.get_plants.assert_called_once()
        self.assertEqual(self.mock_api_instance.get_device_list.call_count, 2)
        self.assertEqual(self.mock_api_instance.get_energy_stats.call_count, 4)  # 2 plants * 2 devices

    def test_collect_and_store_all_data_auth_failure(self):
        """Test data collection with authentication failure"""
        # Configure mocks for auth failure
        self.mock_api_instance.login.return_value = False
        
        # Call collect_and_store_all_data
        result = self.collector.collect_and_store_all_data()
        
        # Verify results
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Authentication failed: Invalid credentials or API error")
        
        # Verify API calls
        self.mock_api_instance.login.assert_called_once()
        self.mock_api_instance.get_plants.assert_not_called()

    def test_collect_and_store_all_data_no_plants(self):
        """Test data collection with no plants returned"""
        # Configure mocks
        self.collector.authenticated = True
        self.mock_api_instance.get_plants.return_value = []
        
        # Call collect_and_store_all_data
        result = self.collector.collect_and_store_all_data()
        
        # Verify results
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "No plants data returned from API")
        
        # Verify API calls
        self.mock_api_instance.get_plants.assert_called_once()
        self.mock_api_instance.get_device_list.assert_not_called()

    def test_collect_and_store_all_data_invalid_plants(self):
        """Test data collection with invalid plants data"""
        # Configure mocks
        self.collector.authenticated = True
        self.mock_api_instance.get_plants.return_value = {"error": "Invalid data"}  # Not a list
        
        # Call collect_and_store_all_data
        result = self.collector.collect_and_store_all_data()
        
        # Verify results
        self.assertFalse(result["success"])
        self.assertTrue("Unexpected plants data format" in result["message"])
        
        # Verify API calls
        self.mock_api_instance.get_plants.assert_called_once()
        self.mock_api_instance.get_device_list.assert_not_called()

    def test_collect_and_store_all_data_partial_failure(self):
        """Test data collection with partial failure"""
        # Configure mocks for partial success
        self.collector.authenticated = True
        
        # Configure API mock returns
        self.mock_api_instance.get_plants.return_value = self.sample_plants
        self.mock_api_instance.get_device_list.side_effect = [
            self.sample_devices,  # First plant successful
            Exception("API error")  # Second plant fails
        ]
        self.mock_api_instance.get_energy_stats.return_value = self.sample_energy_data
        self.mock_api_instance.get_weather.return_value = self.sample_weather_data
        
        # Configure DB mock returns
        self.mock_db_instance.save_plant_data.return_value = True
        self.mock_db_instance.save_device_data.return_value = True
        self.mock_db_instance.save_energy_data_batch.return_value = 2
        self.mock_db_instance.save_weather_data.return_value = True
        
        # Configure tracker mock
        self.mock_tracker_instance.check_and_notify_status_changes.return_value = {
            'offline': 1,
            'online': 0
        }
        
        # Call collect_and_store_all_data
        result = self.collector.collect_and_store_all_data()
        
        # Verify results
        self.assertTrue(result["success"])  # Still success since some data was collected
        self.assertEqual(result["results"]["plants"], 2)
        self.assertEqual(result["results"]["devices"], 2)  # Only first plant's devices
        self.assertTrue(len(result["results"]["errors"]) > 0)  # Error recorded
        self.assertEqual(result["message"], "Data collection completed with some errors")

    def test_collect_device_energy_data(self):
        """Test collecting energy data for a device"""
        # Configure mocks
        self.mock_api_instance.get_energy_stats.return_value = self.sample_energy_data
        self.mock_db_instance.save_energy_data_batch.return_value = 2
        
        # Create results dictionary to update
        results = {"energy_stats": 0, "errors": []}
        
        # Call _collect_device_energy_data
        self.collector._collect_device_energy_data(
            "PLANT001", "DEVICE001", results, days_back=7
        )
        
        # Verify results
        self.assertEqual(results["energy_stats"], 2)
        self.assertEqual(len(results["errors"]), 0)
        
        # Verify API calls
        self.mock_api_instance.get_energy_stats.assert_called_once()
        call_kwargs = self.mock_api_instance.get_energy_stats.call_args[1]
        self.assertEqual(call_kwargs["plant_id"], "PLANT001")
        self.assertEqual(call_kwargs["device_sn"], "DEVICE001")
        
        # Verify date range is correct
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        self.assertEqual(call_kwargs["start_date"], start_date)
        self.assertEqual(call_kwargs["end_date"], end_date)

    def test_collect_weather_data(self):
        """Test collecting weather data for a plant"""
        # Configure mocks
        self.mock_api_instance.get_weather.return_value = self.sample_weather_data
        self.mock_db_instance.save_weather_data.return_value = True
        
        # Create results dictionary to update
        results = {"weather": 0, "errors": []}
        
        # Call _collect_weather_data
        self.collector._collect_weather_data("PLANT001", results)
        
        # Verify results
        self.assertEqual(results["weather"], 1)
        self.assertEqual(len(results["errors"]), 0)
        
        # Verify API calls
        self.mock_api_instance.get_weather.assert_called_once_with("PLANT001")
        
        # Verify DB calls
        self.mock_db_instance.save_weather_data.assert_called_once()
        call_kwargs = self.mock_db_instance.save_weather_data.call_args[1]
        self.assertEqual(call_kwargs["plant_id"], "PLANT001")
        self.assertEqual(call_kwargs["temperature"], self.sample_weather_data["temperature"])
        self.assertEqual(call_kwargs["condition"], self.sample_weather_data["weather"])

    def test_collect_plants_data(self):
        """Test collecting plant data"""
        # Configure mocks
        self.mock_api_instance.get_plants.return_value = self.sample_plants
        self.mock_db_instance.save_plant_data.return_value = True
        
        # Create results dictionary to update
        results = {"plants": 0, "errors": []}
        
        # Call _collect_plants_data
        plants = self.collector._collect_plants_data(results)
        
        # Verify results
        self.assertEqual(results["plants"], 2)
        self.assertEqual(len(results["errors"]), 0)
        self.assertEqual(plants, self.sample_plants)
        
        # Verify API calls
        self.mock_api_instance.get_plants.assert_called_once()
        
        # Verify DB calls
        self.mock_db_instance.save_plant_data.assert_called_once_with(self.sample_plants)

    def test_save_to_json(self):
        """Test saving data to JSON file"""
        # Enable file saving
        self.collector.save_to_file = True
        
        # Create a temporary data directory for testing
        import tempfile
        temp_dir = tempfile.mkdtemp()
        self.collector.data_dir = temp_dir
        
        try:
            # Save test data to JSON
            test_data = {"test": "data"}
            test_filename = "test_data.json"
            self.collector._save_to_json(test_data, test_filename)
            
            # Verify file was created
            file_path = os.path.join(temp_dir, test_filename)
            self.assertTrue(os.path.exists(file_path))
            
            # Verify file contents
            with open(file_path, 'r') as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data, test_data)
        finally:
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir)

    def test_save_to_json_disabled(self):
        """Test saving to JSON when disabled"""
        # Disable file saving
        self.collector.save_to_file = False
        
        # Save test data to JSON
        test_data = {"test": "data"}
        test_filename = "test_data.json"
        self.collector._save_to_json(test_data, test_filename)
        
        # No file should be created
        file_path = os.path.join(self.collector.data_dir, test_filename)
        self.assertFalse(os.path.exists(file_path))

    @patch('app.data_collector.GrowattDataCollector.authenticate')
    def test_collect_device_data_function(self, mock_auth):
        """Test the standalone collect_device_data function"""
        # Configure mocks
        mock_auth.return_value = True
        
        # Patch the necessary methods
        with patch('app.data_collector.GrowattDataCollector._collect_plants_data') as mock_collect_plants, \
             patch('app.data_collector.GrowattDataCollector._safe_api_call') as mock_safe_api, \
             patch('app.data_collector.DeviceStatusTracker.check_all_devices') as mock_check_devices:
            
            # Configure mock returns
            mock_collect_plants.return_value = self.sample_plants
            mock_safe_api.return_value = self.sample_devices
            self.mock_db_instance.save_device_data.return_value = True
            mock_check_devices.return_value = {'offline': 1, 'online': 0}
            
            # Call collect_device_data
            result = collect_device_data()
            
            # Verify results
            self.assertTrue(result["success"])
            self.assertEqual(result["results"]["plants"], 2)
            self.assertEqual(result["results"]["devices"], 2)
            
            # Verify method calls
            mock_auth.assert_called_once()
            mock_collect_plants.assert_called_once()
            self.assertEqual(mock_safe_api.call_count, 2)  # Called once per plant
            mock_check_devices.assert_called_once()

    @patch('app.data_collector.GrowattDataCollector.authenticate')
    def test_collect_plant_data_function(self, mock_auth):
        """Test the standalone collect_plant_data function"""
        # Configure mocks
        mock_auth.return_value = True
        
        # Patch the necessary methods
        with patch('app.data_collector.GrowattDataCollector._collect_plants_data') as mock_collect_plants, \
             patch('app.data_collector.GrowattDataCollector._collect_weather_data') as mock_collect_weather:
            
            # Configure mock returns
            mock_collect_plants.return_value = self.sample_plants
            
            # Call collect_plant_data
            result = collect_plant_data()
            
            # Verify results
            self.assertTrue(result["success"])
            
            # Verify method calls
            mock_auth.assert_called_once()
            mock_collect_plants.assert_called_once()
            self.assertEqual(mock_collect_weather.call_count, 2)  # Called once per plant


if __name__ == '__main__':
    unittest.main()