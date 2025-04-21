import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import shutil
import json
from datetime import date

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the class to test
from app.data_collector import GrowattDataCollector


class TestDataCollector(unittest.TestCase):
    """Test cases for the GrowattDataCollector class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test data
        self.test_data_dir = tempfile.mkdtemp()
        
        # Mock configuration
        self.test_username = "test_user"
        self.test_password = "test_password"
        
        # Sample test data
        self.sample_plants = [
            {"id": "1234567", "plantName": "Test Plant 1"},
            {"id": "7654321", "plantName": "Test Plant 2"}
        ]
        
        self.sample_devices = {
            "result": 1,
            "obj": {
                "totalCount": 2,
                "mix": [
                    ["TESTMIX1", "TESTMIX1", "0"],
                    ["TESTMIX2", "TESTMIX2", "1"]
                ]
            }
        }
        
        self.sample_energy_stats = {
            "obj": {
                "etouser": "5.2",
                "elocalLoad": "12.6",
                "charts": {
                    "ppv": [0, 1, 2, 3, 4],
                    "elocalLoad": [1, 2, 3, 4, 5]
                }
            }
        }
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove the temporary directory
        shutil.rmtree(self.test_data_dir)
    
    @patch('app.core.growatt.Growatt')
    def test_initialization(self, mock_growatt_class):
        """Test collector initialization"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        # Act
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        # Assert
        self.assertEqual(collector.username, self.test_username)
        self.assertEqual(collector.password, self.test_password)
        self.assertTrue(collector.save_to_file)
        self.assertEqual(collector.data_dir, self.test_data_dir)
        self.assertIsNotNone(collector.api)
        mock_growatt_class.assert_called_once()
    
    @patch('app.core.growatt.Growatt')
    def test_initialization_with_defaults(self, mock_growatt_class):
        """Test collector initialization with default parameters"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        # Act
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Assert
        self.assertEqual(collector.username, self.test_username)
        self.assertEqual(collector.password, self.test_password)
        self.assertFalse(collector.save_to_file)
        self.assertEqual(collector.data_dir, os.path.join(os.getcwd(), 'data'))
        self.assertIsNotNone(collector.api)
        mock_growatt_class.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_login_success(self, mock_growatt_class):
        """Test successful login"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector._login()
        
        # Assert
        self.assertTrue(result)
        mock_api.login.assert_called_once_with(self.test_username, self.test_password)

    @patch('app.core.growatt.Growatt')
    def test_login_failure(self, mock_growatt_class):
        """Test login failure"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = False
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector._login()
        
        # Assert
        self.assertFalse(result)
        mock_api.login.assert_called_once_with(self.test_username, self.test_password)

    @patch('app.core.growatt.Growatt')
    def test_collect_plants(self, mock_growatt_class):
        """Test collecting plants data"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.return_value = self.sample_plants
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save:
            plants = collector._collect_plants()
        
        # Assert
        self.assertEqual(plants, self.sample_plants)
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_called_once()
        mock_save.assert_called_once()
    
    @patch('app.core.growatt.Growatt')
    def test_collect_plants_login_failure(self, mock_growatt_class):
        """Test collecting plants data with login failure"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = False
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        plants = collector._collect_plants()
        
        # Assert
        self.assertIsNone(plants)
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_not_called()

    @patch('app.core.growatt.Growatt')
    def test_collect_plants_api_error(self, mock_growatt_class):
        """Test collecting plants data with API error"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.side_effect = Exception("API Error")
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        plants = collector._collect_plants()
        
        # Assert
        self.assertIsNone(plants)
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_collect_devices(self, mock_growatt_class):
        """Test collecting devices data"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_devices_by_plant_list.return_value = self.sample_devices
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save:
            devices = collector._collect_devices(self.sample_plants[0]['id'])
        
        # Assert
        self.assertEqual(devices, self.sample_devices)
        mock_api.get_devices_by_plant_list.assert_called_once_with(self.sample_plants[0]['id'])
        mock_save.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_collect_devices_api_error(self, mock_growatt_class):
        """Test collecting devices data with API error"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_devices_by_plant_list.side_effect = Exception("API Error")
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = self.sample_plants[0]['id']
        
        # Act
        devices = collector._collect_devices(plant_id)
        
        # Assert
        self.assertIsNone(devices)
        mock_api.get_devices_by_plant_list.assert_called_once_with(plant_id)

    @patch('app.core.growatt.Growatt')
    def test_collect_energy_stats(self, mock_growatt_class):
        """Test collecting energy statistics"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_energy_stats_daily.return_value = self.sample_energy_stats
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        plant_id = self.sample_plants[0]['id']
        mix_sn = "TESTMIX1"
        today = date.today().strftime("%Y-%m-%d")
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save:
            stats = collector._collect_energy_stats(plant_id, mix_sn, "daily", today)
        
        # Assert
        self.assertEqual(stats, self.sample_energy_stats)
        mock_api.get_energy_stats_daily.assert_called_once_with(today, plant_id, mix_sn)
        mock_save.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_collect_energy_stats_daily_api_error(self, mock_growatt_class):
        """Test collecting daily energy statistics with API error"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_energy_stats_daily.side_effect = Exception("API Error")
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = self.sample_plants[0]['id']
        mix_sn = "TESTMIX1"
        today = date.today().strftime("%Y-%m-%d")
        
        # Act
        stats = collector._collect_energy_stats(plant_id, mix_sn, "daily", today)
        
        # Assert
        self.assertIsNone(stats)
        mock_api.get_energy_stats_daily.assert_called_once_with(today, plant_id, mix_sn)

    @patch('app.core.growatt.Growatt')
    def test_collect_energy_stats_monthly(self, mock_growatt_class):
        """Test collecting monthly energy statistics"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_energy_stats_monthly.return_value = self.sample_energy_stats
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        plant_id = self.sample_plants[0]['id']
        mix_sn = "TESTMIX1"
        month_year = date.today().strftime("%Y-%m")
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save:
            stats = collector._collect_energy_stats(plant_id, mix_sn, "monthly", month_year)
        
        # Assert
        self.assertEqual(stats, self.sample_energy_stats)
        mock_api.get_energy_stats_monthly.assert_called_once_with(month_year, plant_id, mix_sn)
        mock_save.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_collect_energy_stats_yearly(self, mock_growatt_class):
        """Test collecting yearly energy statistics"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_energy_stats_yearly.return_value = self.sample_energy_stats
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        plant_id = self.sample_plants[0]['id']
        mix_sn = "TESTMIX1"
        year = date.today().strftime("%Y")
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save:
            stats = collector._collect_energy_stats(plant_id, mix_sn, "yearly", year)
        
        # Assert
        self.assertEqual(stats, self.sample_energy_stats)
        mock_api.get_energy_stats_yearly.assert_called_once_with(year, plant_id, mix_sn)
        mock_save.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_collect_energy_stats_invalid_type(self, mock_growatt_class):
        """Test collecting energy statistics with invalid type"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = self.sample_plants[0]['id']
        mix_sn = "TESTMIX1"
        date_str = date.today().strftime("%Y-%m-%d")
        
        # Act
        stats = collector._collect_energy_stats(plant_id, mix_sn, "invalid_type", date_str)
        
        # Assert
        self.assertIsNone(stats)
        mock_api.get_energy_stats_daily.assert_not_called()
        mock_api.get_energy_stats_monthly.assert_not_called()
        mock_api.get_energy_stats_yearly.assert_not_called()

    @patch('app.core.growatt.Growatt')
    def test_save_to_json(self, mock_growatt_class):
        """Test saving data to JSON file"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        test_data = {"test": "data"}
        filename = "test_file.json"
        
        # Act
        collector._save_to_json(test_data, filename)
        
        # Assert
        file_path = os.path.join(self.test_data_dir, filename)
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data, test_data)

    @patch('app.core.growatt.Growatt')
    def test_save_to_json_disabled(self, mock_growatt_class):
        """Test not saving data when save_to_file is False"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=False,
            data_dir=self.test_data_dir
        )
        
        test_data = {"test": "data"}
        filename = "test_file.json"
        
        # Act
        with patch('builtins.open', MagicMock()) as mock_open:
            collector._save_to_json(test_data, filename)
        
        # Assert
        mock_open.assert_not_called()
    
    @patch('app.core.growatt.Growatt')
    def test_save_to_json_file_error(self, mock_growatt_class):
        """Test handling file error when saving to JSON"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        test_data = {"test": "data"}
        filename = "test_file.json"
        
        # Act
        with patch('builtins.open', MagicMock(side_effect=IOError("File error"))):
            result = collector._save_to_json(test_data, filename)
        
        # Assert
        self.assertFalse(result)

    @patch('app.core.growatt.Growatt')
    def test_test_data_collection(self, mock_growatt_class):
        """Test the test data collection mode"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        test_options = {
            'data_type': 'daily',
            'test_date': '2024-08-01',
            'dry_run': False,
            'output_dir': os.path.join(self.test_data_dir, 'test_output')
        }
        
        # Act
        with patch.object(collector, '_generate_test_plants') as mock_gen_plants, \
             patch.object(collector, '_generate_test_devices') as mock_gen_devices, \
             patch.object(collector, '_generate_test_energy_stats') as mock_gen_stats, \
             patch.object(collector, '_save_to_json') as mock_save:
            
            mock_gen_plants.return_value = self.sample_plants
            mock_gen_devices.return_value = self.sample_devices
            mock_gen_stats.return_value = self.sample_energy_stats
            
            result = collector.test_data_collection(test_options)
        
        # Assert
        self.assertTrue(result['success'])
        mock_gen_plants.assert_called_once()
        mock_gen_devices.assert_called()
        mock_gen_stats.assert_called()
        mock_save.assert_called()

    @patch('app.core.growatt.Growatt')
    def test_test_data_collection_dry_run(self, mock_growatt_class):
        """Test the test data collection mode with dry run"""
        # Arrange
        mock_api = MagicMock()
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        test_options = {
            'data_type': 'daily',
            'test_date': '2024-08-01',
            'dry_run': True,
            'output_dir': os.path.join(self.test_data_dir, 'test_output')
        }
        
        # Act
        with patch.object(collector, '_generate_test_plants') as mock_gen_plants, \
             patch.object(collector, '_generate_test_devices') as mock_gen_devices, \
             patch.object(collector, '_generate_test_energy_stats') as mock_gen_stats, \
             patch.object(collector, '_save_to_json') as mock_save:
            
            mock_gen_plants.return_value = self.sample_plants
            mock_gen_devices.return_value = self.sample_devices
            mock_gen_stats.return_value = self.sample_energy_stats
            
            result = collector.test_data_collection(test_options)
        
        # Assert
        self.assertTrue(result['success'])
        mock_gen_plants.assert_called_once()
        mock_gen_devices.assert_called()
        mock_gen_stats.assert_called()
        mock_save.assert_not_called()

    @patch('app.core.growatt.Growatt')
    def test_collect_and_store_all_data(self, mock_growatt_class):
        """Test collecting and storing all data"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.return_value = self.sample_plants
        mock_api.get_devices_by_plant_list.return_value = self.sample_devices
        mock_api.get_energy_stats_daily.return_value = self.sample_energy_stats
        mock_api.get_energy_stats_monthly.return_value = self.sample_energy_stats
        mock_api.get_energy_stats_yearly.return_value = self.sample_energy_stats
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save, \
             patch.object(collector, '_save_to_database') as mock_save_db:
            result = collector.collect_and_store_all_data()
        
        # Assert
        self.assertTrue(result['success'])
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_called_once()
        mock_api.get_devices_by_plant_list.assert_called()
        mock_save.assert_called()

    @patch('app.core.growatt.Growatt')
    def test_collect_and_store_all_data_no_plants(self, mock_growatt_class):
        """Test collecting data when no plants are found"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.return_value = []
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector.collect_and_store_all_data()
        
        # Assert
        self.assertFalse(result['success'])
        self.assertIn('No plants found', result['message'])
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_called_once()
        mock_api.get_devices_by_plant_list.assert_not_called()

    @patch('app.core.growatt.Growatt')
    def test_collect_and_store_all_data_no_devices(self, mock_growatt_class):
        """Test collecting data when no devices are found"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.return_value = self.sample_plants
        mock_api.get_devices_by_plant_list.return_value = {
            "result": 1,
            "obj": {
                "totalCount": 0,
                "mix": []
            }
        }
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector.collect_and_store_all_data()
        
        # Assert
        self.assertFalse(result['success'])
        self.assertIn('No devices found', result['message'])
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_called_once()
        mock_api.get_devices_by_plant_list.assert_called()
        mock_api.get_energy_stats_daily.assert_not_called()

    @patch('app.core.growatt.Growatt')
    def test_collect_and_store_all_data_with_db(self, mock_growatt_class):
        """Test collecting and storing all data with database storage"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.return_value = self.sample_plants
        mock_api.get_devices_by_plant_list.return_value = self.sample_devices
        mock_api.get_energy_stats_daily.return_value = self.sample_energy_stats
        mock_api.get_energy_stats_monthly.return_value = self.sample_energy_stats
        mock_api.get_energy_stats_yearly.return_value = self.sample_energy_stats
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=False,
            save_to_db=True
        )
        
        # Act
        with patch.object(collector, '_save_to_database') as mock_save_db:
            mock_save_db.return_value = True
            result = collector.collect_and_store_all_data()
        
        # Assert
        self.assertTrue(result['success'])
        mock_api.login.assert_called_once()
        mock_api.get_plants.assert_called_once()
        mock_api.get_devices_by_plant_list.assert_called()
        mock_save_db.assert_called()

    @patch('app.core.growatt.Growatt')
    def test_collect_specific_date_range(self, mock_growatt_class):
        """Test collecting data for specific date range"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_api.get_plants.return_value = self.sample_plants
        mock_api.get_devices_by_plant_list.return_value = self.sample_devices
        mock_api.get_energy_stats_daily.return_value = self.sample_energy_stats
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password,
            save_to_file=True,
            data_dir=self.test_data_dir
        )
        
        date_range = {
            'start_date': '2024-05-01',
            'end_date': '2024-05-05'
        }
        
        # Act
        with patch.object(collector, '_save_to_json') as mock_save:
            result = collector.collect_date_range_data(date_range)
        
        # Assert
        self.assertTrue(result['success'])
        self.assertEqual(mock_api.get_energy_stats_daily.call_count, 5 * len(self.sample_devices['obj']['mix']))
        mock_save.assert_called()

    @patch('app.core.growatt.Growatt')
    def test_authenticate_success(self, mock_growatt_class):
        """Test successful authentication with proper error handling"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = True
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector.authenticate()
        
        # Assert
        self.assertTrue(result)
        self.assertTrue(collector.authenticated)
        mock_api.login.assert_called_once_with(username=self.test_username, password=self.test_password)
    
    @patch('app.core.growatt.Growatt')
    def test_authenticate_failure(self, mock_growatt_class):
        """Test authentication failure with retry logic"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.return_value = False
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        collector.retry_count = 2  # Set to 2 for faster test
        
        # Act
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            result = collector.authenticate()
        
        # Assert
        self.assertFalse(result)
        self.assertFalse(collector.authenticated)
        self.assertEqual(mock_api.login.call_count, 2)  # Should retry once
        mock_sleep.assert_called_once()  # Should sleep between retries
    
    @patch('app.core.growatt.Growatt')
    def test_authenticate_exception(self, mock_growatt_class):
        """Test authentication with exception handling"""
        # Arrange
        mock_api = MagicMock()
        mock_api.login.side_effect = Exception("API connection error")
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        collector.retry_count = 2  # Set to 2 for faster test
        
        # Act
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            result = collector.authenticate()
        
        # Assert
        self.assertFalse(result)
        self.assertFalse(collector.authenticated)
        self.assertEqual(mock_api.login.call_count, 2)  # Should retry once
        mock_sleep.assert_called_once()  # Should sleep between retries

    @patch('app.core.growatt.Growatt')
    def test_safe_api_call_success(self, mock_growatt_class):
        """Test the _safe_api_call method with successful execution"""
        # Arrange
        mock_api = MagicMock()
        test_result = {"data": "test_value"}
        mock_api.get_plants = MagicMock(return_value=test_result)
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector._safe_api_call(mock_api.get_plants)
        
        # Assert
        self.assertEqual(result, test_result)
        mock_api.get_plants.assert_called_once()
    
    @patch('app.core.growatt.Growatt')
    def test_safe_api_call_with_args(self, mock_growatt_class):
        """Test the _safe_api_call method with arguments"""
        # Arrange
        mock_api = MagicMock()
        test_result = {"device_data": "value"}
        mock_api.get_device_list = MagicMock(return_value=test_result)
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        
        # Act
        result = collector._safe_api_call(mock_api.get_device_list, plant_id)
        
        # Assert
        self.assertEqual(result, test_result)
        mock_api.get_device_list.assert_called_once_with(plant_id)
    
    @patch('app.core.growatt.Growatt')
    def test_safe_api_call_with_kwargs(self, mock_growatt_class):
        """Test the _safe_api_call method with keyword arguments"""
        # Arrange
        mock_api = MagicMock()
        test_result = {"energy_data": "test_value"}
        mock_api.get_energy_stats = MagicMock(return_value=test_result)
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        result = collector._safe_api_call(
            mock_api.get_energy_stats,
            plant_id="12345",
            device_sn="SN123",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        # Assert
        self.assertEqual(result, test_result)
        mock_api.get_energy_stats.assert_called_once_with(
            plant_id="12345", 
            device_sn="SN123", 
            start_date="2024-01-01", 
            end_date="2024-01-31"
        )
    
    @patch('app.core.growatt.Growatt')
    def test_safe_api_call_exception_with_retry(self, mock_growatt_class):
        """Test the _safe_api_call method with exception and retry"""
        # Arrange
        mock_api = MagicMock()
        side_effects = [
            Exception("First attempt fails"),
            {"data": "success on retry"}
        ]
        mock_api.get_plants = MagicMock(side_effect=side_effects)
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        collector.retry_count = 2  # Set to 2 for faster test
        
        # Act
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            result = collector._safe_api_call(mock_api.get_plants)
        
        # Assert
        self.assertEqual(result, {"data": "success on retry"})
        self.assertEqual(mock_api.get_plants.call_count, 2)
        mock_sleep.assert_called_once()  # Should sleep between retries
    
    @patch('app.core.growatt.Growatt')
    def test_safe_api_call_session_expired(self, mock_growatt_class):
        """Test the _safe_api_call method with session expired error"""
        # Arrange
        mock_api = MagicMock()
        # First call returns session expired, second call succeeds after re-auth
        side_effects = [
            {"error": True, "msg": "session expired"},
            {"data": "success after re-auth"}
        ]
        mock_api.get_plants = MagicMock(side_effect=side_effects)
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        # Act
        with patch.object(collector, 'authenticate') as mock_auth:
            mock_auth.return_value = True
            result = collector._safe_api_call(mock_api.get_plants)
        
        # Assert
        self.assertEqual(result, {"data": "success after re-auth"})
        self.assertEqual(mock_api.get_plants.call_count, 2)
        mock_auth.assert_called_once()  # Should try to re-authenticate

    @patch('app.core.growatt.Growatt')
    def test_collect_device_energy_data(self, mock_growatt_class):
        """Test collecting energy data for a specific device"""
        # Arrange
        mock_api = MagicMock()
        energy_data = {
            "data": [
                {"date": "2024-04-01", "energy": 5.6, "peak_power": 2.1},
                {"date": "2024-04-02", "energy": 4.8, "peak_power": 1.9},
                {"date": "2024-04-03", "energy": 6.2, "peak_power": 2.3}
            ]
        }
        mock_api.get_energy_stats.return_value = energy_data
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        device_sn = "DEVICE001"
        results = {"energy_stats": 0, "errors": []}
        days_back = 3
        
        # Act
        with patch.object(collector.db, 'save_energy_data_batch') as mock_save_batch:
            mock_save_batch.return_value = 3  # 3 records saved
            collector._collect_device_energy_data(plant_id, device_sn, results, days_back)
        
        # Assert
        self.assertEqual(results["energy_stats"], 3)
        self.assertEqual(len(results["errors"]), 0)
        mock_api.get_energy_stats.assert_called_once()
        # Verify correct date range parameters were passed
        args, kwargs = mock_api.get_energy_stats.call_args
        self.assertEqual(kwargs["plant_id"], plant_id)
        self.assertEqual(kwargs["device_sn"], device_sn)
        # Dates should be formatted as strings in YYYY-MM-DD format
        self.assertIsInstance(kwargs["start_date"], str)
        self.assertIsInstance(kwargs["end_date"], str)
        
        expected_batch_data = [
            {'plant_id': plant_id, 'mix_sn': device_sn, 'date': '2024-04-01', 'daily_energy': 5.6, 'peak_power': 2.1},
            {'plant_id': plant_id, 'mix_sn': device_sn, 'date': '2024-04-02', 'daily_energy': 4.8, 'peak_power': 1.9},
            {'plant_id': plant_id, 'mix_sn': device_sn, 'date': '2024-04-03', 'daily_energy': 6.2, 'peak_power': 2.3}
        ]
        mock_save_batch.assert_called_once_with(expected_batch_data)
    
    @patch('app.core.growatt.Growatt')
    def test_collect_device_energy_data_no_data(self, mock_growatt_class):
        """Test collecting energy data when no data is returned"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_energy_stats.return_value = {"data": []}
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        device_sn = "DEVICE001"
        results = {"energy_stats": 0, "errors": []}
        
        # Act
        with patch.object(collector.db, 'save_energy_data_batch') as mock_save_batch:
            collector._collect_device_energy_data(plant_id, device_sn, results)
        
        # Assert
        self.assertEqual(results["energy_stats"], 0)
        mock_api.get_energy_stats.assert_called_once()
        mock_save_batch.assert_not_called()
    
    @patch('app.core.growatt.Growatt')
    def test_collect_device_energy_data_api_error(self, mock_growatt_class):
        """Test collecting energy data when API returns an error"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_energy_stats.side_effect = Exception("API Error")
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        device_sn = "DEVICE001"
        results = {"energy_stats": 0, "errors": []}
        
        # Act
        collector._collect_device_energy_data(plant_id, device_sn, results)
        
        # Assert
        self.assertEqual(results["energy_stats"], 0)
        self.assertEqual(len(results["errors"]), 1)
        self.assertIn(f"Device {device_sn}: API Error", results["errors"][0])
        mock_api.get_energy_stats.assert_called_once()

    @patch('app.core.growatt.Growatt')
    def test_collect_weather_data(self, mock_growatt_class):
        """Test collecting weather data for a plant"""
        # Arrange
        mock_api = MagicMock()
        weather_data = {
            "temperature": 25.6,
            "weather": "Sunny",
            "humidity": 45
        }
        mock_api.get_weather.return_value = weather_data
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        results = {"weather": 0, "errors": []}
        
        # Act
        with patch.object(collector.db, 'save_weather_data') as mock_save_weather:
            mock_save_weather.return_value = True
            collector._collect_weather_data(plant_id, results)
        
        # Assert
        self.assertEqual(results["weather"], 1)
        self.assertEqual(len(results["errors"]), 0)
        mock_api.get_weather.assert_called_once_with(plant_id)
        
        # Verify correct data was passed to save_weather_data
        args, kwargs = mock_save_weather.call_args
        self.assertEqual(kwargs["plant_id"], plant_id)
        self.assertEqual(kwargs["temperature"], 25.6)
        self.assertEqual(kwargs["condition"], "Sunny")
        
    @patch('app.core.growatt.Growatt')
    def test_collect_weather_data_no_data(self, mock_growatt_class):
        """Test collecting weather data when no data is returned"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_weather.return_value = {}
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        results = {"weather": 0, "errors": []}
        
        # Act
        with patch.object(collector.db, 'save_weather_data') as mock_save_weather:
            collector._collect_weather_data(plant_id, results)
        
        # Assert
        self.assertEqual(results["weather"], 0)
        mock_api.get_weather.assert_called_once_with(plant_id)
        mock_save_weather.assert_not_called()
        
    @patch('app.core.growatt.Growatt')
    def test_collect_weather_data_with_error(self, mock_growatt_class):
        """Test collecting weather data with API error"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_weather.side_effect = Exception("Weather API error")
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        plant_id = "12345"
        results = {"weather": 0, "errors": []}
        
        # Act
        collector._collect_weather_data(plant_id, results)
        
        # Assert
        self.assertEqual(results["weather"], 0)
        self.assertEqual(len(results["errors"]), 1)
        self.assertTrue(any("Weather for plant" in error for error in results["errors"]))
        mock_api.get_weather.assert_called_once_with(plant_id)
    
    @patch('app.core.growatt.Growatt')
    def test_collect_plants_data(self, mock_growatt_class):
        """Test collecting plants data method"""
        # Arrange
        mock_api = MagicMock()
        mock_api.get_plants.return_value = self.sample_plants
        mock_growatt_class.return_value = mock_api
        
        collector = GrowattDataCollector(
            username=self.test_username,
            password=self.test_password
        )
        
        results = {"plants": 0, "errors": []}
        
        # Act
        with patch.object(collector.db, 'save_plant_data') as mock_save_plants:
            mock_save_plants.return_value = True
            plants = collector._collect_plants_data(results)
        
        # Assert
        self.assertEqual(len(plants), 2)
        self.assertEqual(results["plants"], 2)
        self.assertEqual(len(results["errors"]), 0)
        mock_api.get_plants.assert_called_once()
        mock_save_plants.assert_called_once_with(self.sample_plants)


if __name__ == '__main__':
    unittest.main()
