#!/usr/bin/env python3
"""
Devices Data Collector Tests

This module contains tests for the DevicesDataCollector class.
These tests use real connections to databases and APIs (no mocking).
"""

import os
import sys
import unittest
from datetime import datetime
import psycopg2
import json
import time

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from script.devices_data_collector import DevicesDataCollector
from app.config import Config


class TestDevicesDataCollector(unittest.TestCase):
    """Tests for the DevicesDataCollector class"""

    def setUp(self):
        """Set up the test by creating a collector instance"""
        self.collector = DevicesDataCollector()
    
    def test_database_connection(self):
        """Test that we can connect to the database"""
        conn = self.collector.connect_to_db()
        self.assertIsNotNone(conn)
        conn.close()
    
    def test_ensure_table_exists(self):
        """Test that the device_snapshots table is created properly"""
       