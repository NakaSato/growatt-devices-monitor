#!/usr/bin/env python3
"""
Devices Data Collector Test

This script tests the functionality of the DevicesDataCollector class.
It can test individual components or the entire collection process with mock responses.
"""

import os
import sys
import unittest
import json
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime
from tempfile import NamedTemporaryFile

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.collectors.devices_data_collector import DevicesDataCollector, run_collection
from app.config import Config

# Configure logging to stdout only for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_devices_collector")


class TestDevicesDataCollector(unittest.TestCase):
    """Tests for the DevicesDataCollector class"""

    def setUp(self):
        """Set up test environment before each test case"""
        self.collector = DevicesDataCollector()
        
        # Create mock success responses
        self.mock_auth_response = MagicMock()
        self.mock_auth_response.status_code = 200
        self.mock_auth_response.json.return_value = {"status": "success"}
        
        self.mock_devices_response = MagicMock()
        self.mock_devices_response.status_code = 200
        
        # Sample device data for tests
        self.sample_devices = [
            {
                "serial_number": "SAMPLE001",
                "plant_id": "12345",
                "plant_name": "Test Plant 1",
                "alias": "Inverter 1",
                "status": "online",
                "total_energy": "1234.56",
                "last_update_time": "2023-05-07T08:00:00"
            },
            {
                "serial_number": "SAMPLE002",
                "plant_id": "12345",
                "plant_name": "Test Plant 1",
                "alias": "Inverter 2",
                "status": "offline",
                "total_energy": "5678.90",
                "last_update_time": "2023-05-07T07:00:00"
            }
        ]
        self.mock_devices_response.json.return_value = self.sample_devices

    def test_init(self):
        """Test collector initialization"""
        self.assertEqual(self.collector.base_url, "http://localhost:8000")
        self.assertFalse(self.collector.is_authenticated)
        
        # Test that config values are being used
        self.assertEqual(self.collector.pg_host, Config.POSTGRES_HOST)
        self.assertEqual(self.collector.pg_port, Config.POSTGRES_PORT)
        self.assertEqual(self.collector.pg_user, Config.POSTGRES_USER)
        self.assertEqual(self.collector.pg_password, Config.POSTGRES_PASSWORD)
        self.assertEqual(self.collector.pg_db, Config.POSTGRES_DB)

    @patch('requests.Session.post')
    def test_authenticate_success(self, mock_post):
        """Test successful authentication"""
        mock_post.return_value = self.mock_auth_response
        
        # Test authentication
        result = self.collector.authenticate()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.collector.is_authenticated)
        mock_post.assert_called_once()
        self.assertIn("/api/access", mock_post.call_args.args[0])

    @patch('requests.Session.post')
    def test_authenticate_failure(self, mock_post):
        """Test authentication failure"""
        # Set up mock to return error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        # Test authentication
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.is_authenticated)
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_authenticate_exception(self, mock_post):
        """Test authentication with exception"""
        # Set up mock to raise exception
        mock_post.side_effect = Exception("Connection error")
        
        # Test authentication
        result = self.collector.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.collector.is_authenticated)
        mock_post.assert_called_once()

    @patch('requests.Session.get')
    def test_fetch_devices_success(self, mock_get):
        """Test successful device fetching"""
        # Set up mock response
        mock_get.return_value = self.mock_devices_response
        
        # Test fetching devices
        result = self.collector.fetch_devices()
        
        # Verify results
        self.assertEqual(result, self.sample_devices)
        mock_get.assert_called_once()
        self.assertIn("/api/devices", mock_get.call_args.args[0])

    @patch('requests.Session.get')
    def test_fetch_devices_retry(self, mock_get):
        """Test device fetching with retries"""
        # First response fails, second succeeds
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Server error"
        
        mock_get.side_effect = [mock_error_response, self.mock_devices_response]
        
        # Test fetching devices
        result = self.collector.fetch_devices()
        
        # Verify results
        self.assertEqual(result, self.sample_devices)
        self.assertEqual(mock_get.call_count, 2)

    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_ensure_table_exists(self, mock_connect_db):
        """Test database table creation"""
        # Create mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect_db.return_value = mock_conn
        
        # Configure mock cursor for table check
        mock_cursor.fetchone.return_value = [False]  # Table doesn't exist
        
        # Test table creation
        result = self.collector.ensure_table_exists()
        
        # Verify results
        self.assertTrue(result)
        mock_connect_db.assert_called_once()
        # Check that CREATE TABLE was called
        create_calls = [call for call in mock_cursor.execute.call_args_list if 'CREATE TABLE' in str(call)]
        self.assertTrue(len(create_calls) > 0)

    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.connect_to_db')
    def test_save_devices_to_db(self, mock_connect_db):
        """Test saving devices to database"""
        # Create mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect_db.return_value = mock_conn
        
        # Configure mock cursor for column check
        mock_cursor.fetchall.return_value = [['serial_number'], ['plant_id'], ['plant_name'], 
                                            ['alias'], ['status'], ['total_energy'], 
                                            ['last_update_time'], ['raw_data'], ['collected_at']]
        
        # Test saving devices
        result = self.collector.save_devices_to_db(self.sample_devices)
        
        # Verify results
        self.assertTrue(result)
        mock_connect_db.assert_called_once()
        # Check that INSERT was called for each device
        insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO' in str(call)]
        self.assertEqual(len(insert_calls), len(self.sample_devices))

    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_success(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test successful run of collector"""
        # Configure mocks
        mock_auth.return_value = True
        mock_ensure.return_value = True
        mock_fetch.return_value = self.sample_devices
        mock_save.return_value = True
        
        # Test running collector
        result = self.collector.run()
        
        # Verify results
        self.assertTrue(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save.assert_called_once_with(self.sample_devices)

    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.authenticate')
    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.ensure_table_exists')
    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.fetch_devices')
    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.save_devices_to_db')
    def test_run_failure(self, mock_save, mock_fetch, mock_ensure, mock_auth):
        """Test collector run with failure"""
        # Configure mocks - authentication fails
        mock_auth.return_value = False
        mock_ensure.return_value = True
        
        # Test running collector
        result = self.collector.run()
        
        # Verify results
        self.assertFalse(result)
        mock_ensure.assert_called_once()
        mock_auth.assert_called_once()
        mock_fetch.assert_not_called()
        mock_save.assert_not_called()

    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.run')
    def test_run_collection(self, mock_run):
        """Test the run_collection function"""
        # Configure mock
        mock_run.return_value = True
        
        # Test run_collection
        result = run_collection()
        
        # Verify results
        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('scripts.collectors.devices_data_collector.DevicesDataCollector.run')
    def test_run_collection_exception(self, mock_run):
        """Test the run_collection function with exception"""
        # Configure mock to raise exception
        mock_run.side_effect = Exception("Test exception")
        
        # Test run_collection
        result = run_collection()
        
        # Verify results
        self.assertFalse(result)
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()