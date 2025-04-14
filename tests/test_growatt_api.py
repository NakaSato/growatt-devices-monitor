import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
from datetime import datetime

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.growatt import Growatt


class MockResponse:
    """Mock class for requests.Response"""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")


class TestGrowattAPI(unittest.TestCase):
    """Test cases for the Growatt API client"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api = Growatt()
        self.test_username = "test_user"
        self.test_password = "test_password"
        self.test_plant_id = "1234567"
        self.test_mix_sn = "TESTMIXSN123"
    
    @patch('requests.Session.post')
    def test_login_success(self, mock_post):
        """Test successful login"""
        # Configure mock
        mock_response = MockResponse({"result": 1})
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.api.login(self.test_username, self.test_password)
        
        # Assert results
        self.assertTrue(result)
        self.assertTrue(self.api.is_logged_in)
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_login_failure(self, mock_post):
        """Test failed login"""
        # Configure mock
        mock_response = MockResponse({"result": 0})
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.api.login(self.test_username, self.test_password)
        
        # Assert results
        self.assertFalse(result)
        self.assertFalse(self.api.is_logged_in)
    
    @patch('requests.Session.get')
    def test_logout_success(self, mock_get):
        """Test successful logout"""
        # Set up logged in state
        self.api.is_logged_in = True
        
        # Configure mock
        mock_get.return_value = MockResponse({}, 302)
        
        # Call the method
        result = self.api.logout()
        
        # Assert results
        self.assertTrue(result)
        self.assertFalse(self.api.is_logged_in)
    
    @patch('requests.Session.post')
    def test_get_plants(self, mock_post):
        """Test getting plants list"""
        # Configure mock
        test_plants = [
            {"timezone": "1", "id": "1234567", "plantName": "Test Plant 1"},
            {"timezone": "2", "id": "7654321", "plantName": "Test Plant 2"}
        ]
        mock_post.return_value = MockResponse(test_plants)
        
        # Call the method
        result = self.api.get_plants()
        
        # Assert results
        self.assertEqual(result, test_plants)
        mock_post.assert_called_once_with(f"{self.api.BASE_URL}/index/getPlantListTitle")
    
    @patch('requests.Session.post')
    def test_get_plant(self, mock_post):
        """Test getting a single plant's details"""
        # Configure mock
        test_plant = {
            "country": "Test Country",
            "plantName": "Test Plant",
            "id": self.test_plant_id,
            "nominalPower": "5000"
        }
        mock_post.return_value = MockResponse({"obj": test_plant})
        
        # Call the method
        result = self.api.get_plant(self.test_plant_id)
        
        # Assert results
        self.assertEqual(result, test_plant)
        mock_post.assert_called_once_with(f"{self.api.BASE_URL}/panel/getPlantData?plantId={self.test_plant_id}")
    
    @patch('requests.Session.post')
    def test_get_mix_ids(self, mock_post):
        """Test getting MIX IDs for a plant"""
        # Configure mock
        test_mix_ids = [["TESTMIX1", "TESTMIX1", "0"], ["TESTMIX2", "TESTMIX2", "1"]]
        mock_post.return_value = MockResponse({"obj": {"mix": test_mix_ids}})
        
        # Call the method
        result = self.api.get_mix_ids(self.test_plant_id)
        
        # Assert results
        self.assertEqual(result, test_mix_ids)
        mock_post.assert_called_once_with(f"{self.api.BASE_URL}/panel/getDevicesByPlant?plantId={self.test_plant_id}")
    
    @patch('requests.Session.post')
    def test_get_mix_total(self, mock_post):
        """Test getting total measurements from MIX"""
        # Configure mock
        test_total = {
            "epvTotal": "6115.3",
            "elocalLoadTotal": "6171",
            "etogridTotal": "2568.6"
        }
        mock_post.return_value = MockResponse({"obj": test_total})
        
        # Call the method
        result = self.api.get_mix_total(self.test_plant_id, self.test_mix_sn)
        
        # Assert results
        self.assertEqual(result, test_total)
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_get_mix_status(self, mock_post):
        """Test getting status from MIX"""
        # Configure mock
        test_status = {
            "SOC": "95",
            "ppv": "1.18",
            "status": "5"
        }
        mock_post.return_value = MockResponse({"obj": test_status})
        
        # Call the method
        result = self.api.get_mix_status(self.test_plant_id, self.test_mix_sn)
        
        # Assert results
        self.assertEqual(result, test_status)
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_get_energy_stats_daily(self, mock_post):
        """Test getting daily energy statistics"""
        # Configure mock
        test_date = "2024-08-01"
        test_stats = {
            "etouser": "5.2",
            "elocalLoad": "12.6"
        }
        mock_post.return_value = MockResponse({"obj": test_stats})
        
        # Call the method
        result = self.api.get_energy_stats_daily(test_date, self.test_plant_id, self.test_mix_sn)
        
        # Assert results
        self.assertEqual(result["obj"], test_stats)
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_get_weather(self, mock_post):
        """Test getting weather data"""
        # Configure mock
        test_weather = {
            "temperature": "25.5",
            "humidity": "60%"
        }
        mock_post.return_value = MockResponse(test_weather)
        
        # Call the method
        result = self.api.get_weather(self.test_plant_id)
        
        # Assert results
        self.assertEqual(result, test_weather)
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_get_devices_by_plant_list(self, mock_post):
        """Test getting devices by plant list"""
        # Configure mock
        test_devices = {
            "result": 1,
            "obj": {
                "totalCount": 2,
                "mix": ["device1", "device2"]
            }
        }
        mock_post.return_value = MockResponse(test_devices)
        
        # Call the method
        result = self.api.get_devices_by_plant_list(self.test_plant_id)
        
        # Assert results
        self.assertEqual(result, test_devices)
        mock_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
