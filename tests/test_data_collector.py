import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import tempfile
import shutil
import json
from datetime import datetime, date

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


if __name__ == '__main__':
    unittest.main()
