#!/usr/bin/env python3
"""
Test file for DevicesDataCollector in script/devices_data_collector.py
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import json
import psycopg2
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the class we're testing
from script.devices_data_collector import DevicesDataCollector, run_collection


class TestDevicesDataCollector(unittest.TestCase):
    """Tests for the DevicesDataCollector class"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create a collector instance with mocked config
        with patch('script.devices_data_collector.Config') as mock_config:
            # Configure mock config
            mock_config.API_BASE_URL = "http://test-api.example.com"
            mock_config.POSTGRES_HOST = "test-host"
            mock_config.POSTGRES_PORT = "5432"
            mock_config.POSTGRES_USER = "test-user"
            mock_config.POSTGRES_PASSWORD = "test-password"
            mock_config.POSTGRES_DB = "test-db"
            mock_config.GROWATT_USERNAME = "test-username"
            mock_config.GROWATT_PASSWORD = "test-password"
            
            self.collector = DevicesDataCollector()
        
        # Sample data for tests
        self.sample_devices = [
            {
                "serial_number": "DEVICE001",
                "plant_id": "PLANT001",
                "plant_name": "Test Plant 1",
                "alias": "Inverter 1",
                "status": "normal",
                "total_energy": "1234.56",
                "last_update_time": "2025-05-07 08:00:00"
            },
            {
                "serial_number": "DEVICE002",
                "plant_id": "PLANT001",
                "plant_name": "Test Plant 1",
                "alias": "Inverter 2",
                "status": "offline",
                "total_energy": "5678.90",
                "last_update_time": "2025-05-07 07:00:00"
            }
        ]

    def test_init(self):
        """Test the initialization of the collector"""
        # Verify that the collector has the correct attributes
        self.assertEqual(self.collector.base_url, "http://test-api.example.com")
        self.assertEqual(self.collector.pg_host, "test-host")
        self.assertEqual(self.collector.pg_port, "5432")
        self.assertEqual(self.collector.pg_user, "test-user")
        self.assertEqual(self.collector.pg_password, "test-password")
        self.assertEqual(self.collector.pg_db, "test-db")
        self.assertFalse(self.collector.is_authenticated)

    @patch('requests.Session.post')
    def test_authenticate_success(self, mock_post):
        """Test successful authentication with the API"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        # Call authenticate method
        result = self.collector.authenticate()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.collector.is_authenticated)
        mock_post.assert_called_once()
        # Verify the correct URL and data were used
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "http://test-api.example.com/api/access")
        self.assertEqual(call_args[1]["data"]["username"], "test-username")
        self.assertEqual(call_args[1]["data"]["password"], "test-password")

    @patch('requests.Session.post')
    def test_authenticate_http_error(self, mock_post):
        """Test authentication with HTTP error response"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        # Call authenticate method
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.is_authenticated)

    @patch('requests.Session.post')
    def test_authenticate_api_error(self, mock_post):
        """Test authentication with API error response"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "Invalid credentials"}
        mock_post.return_value = mock_response
        
        # Call authenticate method
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.is_authenticated)

    @patch('requests.Session.post')
    def test_authenticate_connection_error(self, mock_post):
        """Test authentication with connection error"""
        # Configure mock to raise exception
        mock_post.side_effect = Exception("Connection error")
        
        # Call authenticate method
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.is_authenticated)

    @patch('requests.Session.get')
    def test_fetch_devices_success(self, mock_get):
        """Test successful device fetching"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_devices
        mock_get.return_value = mock_response
        
        # Call fetch_devices method
        result = self.collector.fetch_devices()
        
        # Verify results
        self.assertEqual(result, self.sample_devices)
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args[0][0], "http://test-api.example.com/api/devices")

    @patch('requests.Session.get')
    def test_fetch_devices_retry_on_error(self, mock_get):
        """Test device fetching with retry on error"""
        # Configure first mock response as error, second as success
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Server error"
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = self.sample_devices
        
        mock_get.side_effect = [mock_error_response, mock_success_response]
        
        # Call fetch_devices method
        result = self.collector.fetch_devices()
        
        # Verify results
        self.assertEqual(result, self.sample_devices)
        self.assertEqual(mock_get.call_count, 2)

    @patch('requests.Session.get')
    def test_fetch_devices_json_error(self, mock_get):
        """Test fetch devices with JSON parsing error"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Not a valid JSON"
        mock_get.return_value = mock_response
        
        # Call fetch_devices method
        result = self.collector.fetch_devices()
        
        # Verify results
        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, 3)  # Should retry max_retries times

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_ensure_table_exists_table_exists(self, mock_connect):
        """Test ensure_table_exists when the table already exists"""
        # Configure mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Configure cursor.fetchone to indicate table exists
        mock_cursor.fetchone.return_value = [True]
        
        # Configure cursor.fetchall to return column names
        mock_cursor.fetchall.return_value = [
            ['id'], ['serial_number'], ['plant_id'], ['plant_name'], 
            ['alias'], ['status'], ['total_energy'], 
            ['last_update_time'], ['raw_data'], ['collected_at']
        ]
        
        # Call ensure_table_exists method
        result = self.collector.ensure_table_exists()
        
        # Verify results
        self.assertTrue(result)
        mock_connect.assert_called_once()
        # Table should not be created if it exists
        create_calls = [call for call in mock_cursor.execute.call_args_list if 'CREATE TABLE' in str(call)]
        self.assertEqual(len(create_calls), 0)

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_ensure_table_exists_table_missing(self, mock_connect):
        """Test ensure_table_exists when the table does not exist"""
        # Configure mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Configure cursor.fetchone to indicate table does not exist
        mock_cursor.fetchone.return_value = [False]
        
        # Call ensure_table_exists method
        result = self.collector.ensure_table_exists()
        
        # Verify results
        self.assertTrue(result)
        mock_connect.assert_called_once()
        # Table should be created if it doesn't exist
        create_calls = [call for call in mock_cursor.execute.call_args_list if 'CREATE TABLE' in str(call)]
        self.assertEqual(len(create_calls), 1)

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_ensure_table_exists_db_error(self, mock_connect):
        """Test ensure_table_exists with database error"""
        # Configure mock to raise exception
        mock_connect.side_effect = psycopg2.OperationalError("Connection refused")
        
        # Call ensure_table_exists method
        result = self.collector.ensure_table_exists()
        
        # Verify results
        self.assertFalse(result)
        mock_connect.assert_called_once()

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_save_devices_to_db_success(self, mock_connect):
        """Test successful saving of devices to database"""
        # Configure mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Configure cursor.fetchall to return column names
        mock_cursor.fetchall.return_value = [
            ['serial_number'], ['plant_id'], ['plant_name'], 
            ['alias'], ['status'], ['total_energy'], 
            ['last_update_time'], ['raw_data'], ['collected_at']
        ]
        
        # Call save_devices_to_db method
        result = self.collector.save_devices_to_db(self.sample_devices)
        
        # Verify results
        self.assertTrue(result)
        mock_connect.assert_called_once()
        # Should execute insert for each device
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO devices' in str(call)]
        self.assertEqual(len(insert_calls), len(self.sample_devices))

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_save_devices_to_db_empty_list(self, mock_connect):
        """Test saving an empty list of devices"""
        # Call save_devices_to_db method with empty list
        result = self.collector.save_devices_to_db([])
        
        # Verify results
        self.assertFalse(result)
        mock_connect.assert_not_called()

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_save_devices_to_db_missing_columns(self, mock_connect):
        """Test saving devices when table is missing columns"""
        # Configure mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Configure cursor.fetchall to return incomplete column list
        mock_cursor.fetchall.return_value = [
            ['serial_number'], ['plant_id']  # Missing several columns
        ]
        
        # Call save_devices_to_db method
        result = self.collector.save_devices_to_db(self.sample_devices)
        
        # Verify results
        self.assertTrue(result)
        mock_connect.assert_called_once()
        # Should add missing columns
        alter_calls = [call for call in mock_cursor.execute.call_args_list if 'ALTER TABLE' in str(call)]
        self.assertGreater(len(alter_calls), 0)

    @patch('script.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_save_devices_to_db_db_error(self, mock_connect):
        """Test save_devices_to_db with database error"""
        # Configure mock to raise exception
        mock_connect.side_effect = psycopg2.OperationalError("Connection refused")
        
        # Call save_devices_to_db method
        result = self.collector.save_devices_to_db(self.sample_devices)
        
        # Verify results
        self.assertFalse(result)
        mock_connect.assert_called_once()

    @patch('script.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('script.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('script.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('script.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_success(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test successful run of the collector"""
        # Configure mocks
        mock_ensure.return_value = True
        mock_auth.return_value = True
        mock_fetch.return_value = self.sample_devices
        mock_save.return_value = True
        
        # Call run method
        result = self.collector.run()
        
        # Verify results
        self.assertTrue(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save.assert_called_once_with(self.sample_devices)

    @patch('script.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('script.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('script.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('script.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_table_error(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test run with table creation error"""
        # Configure mocks
        mock_ensure.return_value = False
        
        # Call run method
        result = self.collector.run()
        
        # Verify results
        self.assertFalse(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_not_called()
        mock_fetch.assert_not_called()
        mock_save.assert_not_called()

    @patch('script.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('script.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('script.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('script.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_auth_error(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test run with authentication error"""
        # Configure mocks
        mock_ensure.return_value = True
        mock_auth.return_value = False
        
        # Call run method
        result = self.collector.run()
        
        # Verify results
        self.assertFalse(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_called_once()
        mock_fetch.assert_not_called()
        mock_save.assert_not_called()

    @patch('script.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('script.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('script.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('script.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_fetch_error(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test run with fetch error"""
        # Configure mocks
        mock_ensure.return_value = True
        mock_auth.return_value = True
        mock_fetch.return_value = None
        
        # Call run method
        result = self.collector.run()
        
        # Verify results
        self.assertFalse(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save.assert_not_called()

    @patch('script.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('script.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('script.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('script.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_save_error(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test run with save error"""
        # Configure mocks
        mock_ensure.return_value = True
        mock_auth.return_value = True
        mock_fetch.return_value = self.sample_devices
        mock_save.return_value = False
        
        # Call run method
        result = self.collector.run()
        
        # Verify results
        self.assertFalse(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save.assert_called_once_with(self.sample_devices)

    @patch('script.devices_data_collector.DevicesDataCollector.run')
    def test_run_collection_success(self, mock_run):
        """Test the run_collection function success case"""
        # Configure mock
        mock_run.return_value = True
        
        # Call run_collection function
        result = run_collection()
        
        # Verify results
        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('script.devices_data_collector.DevicesDataCollector.run')
    def test_run_collection_failure(self, mock_run):
        """Test the run_collection function failure case"""
        # Configure mock
        mock_run.return_value = False
        
        # Call run_collection function
        result = run_collection()
        
        # Verify results
        self.assertFalse(result)
        mock_run.assert_called_once()

    @patch('script.devices_data_collector.DevicesDataCollector.run')
    def test_run_collection_exception(self, mock_run):
        """Test the run_collection function with exception"""
        # Configure mock to raise exception
        mock_run.side_effect = Exception("Test exception")
        
        # Call run_collection function
        result = run_collection()
        
        # Verify results
        self.assertFalse(result)
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()