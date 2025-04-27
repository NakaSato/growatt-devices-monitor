import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import tempfile
import shutil
from datetime import datetime

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import after path setup
import script.data_sync as data_sync
from app.data_collector import GrowattDataCollector


class TestDataSync(unittest.TestCase):
    """Test cases for the data synchronization script"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test data
        self.test_data_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove the temporary directory
        shutil.rmtree(self.test_data_dir)
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('app.data_collector.GrowattDataCollector')
    @patch('app.database.init_db')
    def test_main_normal_mode(self, mock_init_db, mock_collector_class, mock_parse_args):
        """Test main function in normal mode"""
        # Configure mocks
        mock_args = MagicMock()
        mock_args.init = True
        mock_args.test = False
        mock_args.verbose = False
        mock_args.username = "test_user"
        mock_args.password = "test_pass"
        mock_parse_args.return_value = mock_args
        
        mock_collector = MagicMock()
        mock_collector.collect_and_store_all_data.return_value = {
            "success": True,
            "results": {
                "plants": 2,
                "devices": 3,
                "energy_stats": 10,
                "weather": 2,
                "errors": []
            }
        }
        mock_collector_class.return_value = mock_collector
        
        # Call the function
        with patch('os.path.exists', return_value=True):
            data_sync.main()
        
        # Verify behavior
        mock_init_db.assert_called_once()
        mock_collector_class.assert_called_once()
        mock_collector.collect_and_store_all_data.assert_called_once()
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('app.data_collector.GrowattDataCollector')
    @patch('app.database.init_db')
    def test_main_test_mode(self, mock_init_db, mock_collector_class, mock_parse_args):
        """Test main function in test mode"""
        # Configure mocks
        mock_args = MagicMock()
        mock_args.init = False
        mock_args.test = True
        mock_args.collect = "daily"
        mock_args.date = "2024-08-01"
        mock_args.dry_run = True
        mock_args.verbose = True
        mock_args.username = None
        mock_args.password = None
        mock_parse_args.return_value = mock_args
        
        mock_collector = MagicMock()
        mock_collector.test_data_collection.return_value = {
            "success": True,
            "results": {
                "plants": 1,
                "devices": 2,
                "energy_stats": 5,
                "weather": 1,
                "errors": []
            }
        }
        mock_collector_class.return_value = mock_collector
        
        # Call the function
        with patch('os.path.exists', return_value=True), \
             patch('logging.FileHandler'), \
             patch('os.makedirs'):
            data_sync.main()
        
        # Verify behavior
        mock_init_db.assert_not_called()
        mock_collector_class.assert_called_once()
        mock_collector.test_data_collection.assert_called_once()
        self.assertEqual(mock_collector.collect_and_store_all_data.call_count, 0)
    
    @patch('argparse.ArgumentParser.parse_args')
    @patch('app.data_collector.GrowattDataCollector')
    def test_main_error_handling(self, mock_collector_class, mock_parse_args):
        """Test main function error handling"""
        # Configure mocks
        mock_args = MagicMock()
        mock_args.init = False
        mock_args.test = False
        mock_args.verbose = False
        mock_args.username = "test_user"
        mock_args.password = "test_pass"
        mock_parse_args.return_value = mock_args
        
        mock_collector = MagicMock()
        mock_collector.collect_and_store_all_data.return_value = {
            "success": False,
            "message": "API error"
        }
        mock_collector_class.return_value = mock_collector
        
        # Call the function
        with patch('os.path.exists', return_value=True), \
             patch('logging.info'), \
             patch('logging.error') as mock_error:
            data_sync.main()
        
        # Verify error was logged
        mock_error.assert_called_with("Data sync failed: API error")


if __name__ == '__main__':
    unittest.main()
