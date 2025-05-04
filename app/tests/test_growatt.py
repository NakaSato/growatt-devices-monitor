import unittest
from unittest.mock import patch, MagicMock
import json
import hashlib
from datetime import datetime
import requests

# Import the Growatt class
from app.core.growatt import Growatt


class TestGrowatt(unittest.TestCase):
    """Test cases for the Growatt API client."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.growatt = Growatt()
        self.test_username = "PWA_solar"
        self.test_password = "123456"
        self.test_plant_id = "1234567"
        self.test_mix_sn = "ABCDEF123456"

    def test_hash_password(self):
        """Test password hashing function."""
        password = "mySecurePassword123"
        expected_hash = hashlib.md5(password.encode()).hexdigest()
        actual_hash = self.growatt._hash_password(password)
        self.assertEqual(expected_hash, actual_hash)

    @patch('requests.Session.post')
    def test_login_success(self, mock_post):
        """Test successful login."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": 1}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.login(self.test_username, self.test_password)
        
        # Verify
        self.assertTrue(result)
        self.assertTrue(self.growatt.is_logged_in)
        mock_post.assert_called_once()
        
        # Verify call parameters
        call_args = mock_post.call_args.args[0]
        call_kwargs = mock_post.call_args.kwargs
        self.assertTrue(call_args.endswith('/login'))
        self.assertIn('data', call_kwargs)
        self.assertEqual(call_kwargs['data']['account'], self.test_username)
        self.assertEqual(call_kwargs['data']['passwordCrc'], self.growatt._hash_password(self.test_password))

    @patch('requests.Session.post')
    def test_login_failure(self, mock_post):
        """Test login failure."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": 0, "msg": "Invalid credentials"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.login(self.test_username, self.test_password)
        
        # Verify
        self.assertFalse(result)
        self.assertFalse(self.growatt.is_logged_in)

    @patch('requests.Session.post')
    def test_login_already_logged_in(self, mock_post):
        """Test login when already logged in."""
        # Set logged in state
        self.growatt.is_logged_in = True
        
        # Test
        result = self.growatt.login(self.test_username, self.test_password)
        
        # Verify
        self.assertTrue(result)
        mock_post.assert_not_called()  # No API call should be made

    @patch('requests.Session.post')
    def test_login_http_error(self, mock_post):
        """Test login with HTTP error."""
        # Mock response with HTTP error
        mock_post.side_effect = requests.exceptions.HTTPError("404 Not Found")

        # Test
        with self.assertRaises(ValueError):
            self.growatt.login(self.test_username, self.test_password)
            
        # Verify
        # In the implementation, is_logged_in is explicitly set to False
        self.assertFalse(self.growatt.is_logged_in)

    @patch('requests.Session.post')
    def test_login_json_error(self, mock_post):
        """Test login with JSON decode error."""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Not a JSON response"
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        with self.assertRaises(ValueError):
            self.growatt.login(self.test_username, self.test_password)
            
        # Verify
        self.assertFalse(self.growatt.is_logged_in)

    @patch('requests.Session.get')
    def test_logout_success(self, mock_get):
        """Test successful logout."""
        # Set up
        self.growatt.is_logged_in = True
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 302  # Redirect status code
        mock_get.return_value = mock_response

        # Test
        result = self.growatt.logout()
        
        # Verify
        self.assertTrue(result)
        self.assertFalse(self.growatt.is_logged_in)
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_logout_failure(self, mock_get):
        """Test logout failure."""
        # Set up
        self.growatt.is_logged_in = True
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 500  # Error status code
        mock_get.return_value = mock_response

        # Test
        result = self.growatt.logout()
        
        # Verify
        self.assertFalse(result)
        self.assertTrue(self.growatt.is_logged_in)  # Still logged in

    def test_logout_not_logged_in(self):
        """Test logout when not logged in."""
        # Set up - ensure not logged in
        self.growatt.is_logged_in = False
        
        # Test
        result = self.growatt.logout()
        
        # Verify
        self.assertFalse(result)

    @patch('requests.Session.post')
    def test_get_plants(self, mock_post):
        """Test getting plants list."""
        # Sample data
        mock_plants = [
            {"timezone": "1", "id": "1234567", "plantName": "Test Plant"}
        ]
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_plants
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.get_plants()
        
        # Verify
        self.assertEqual(result, mock_plants)
        mock_post.assert_called_once()
        self.assertTrue(mock_post.call_args.args[0].endswith('/index/getPlantListTitle'))

    @patch('requests.Session.post')
    def test_get_plants_empty_response(self, mock_post):
        """Test getting plants with empty response."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = None
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        with self.assertRaises(ValueError):
            self.growatt.get_plants()

    @patch('requests.Session.post')
    def test_get_plant(self, mock_post):
        """Test getting specific plant information."""
        # Sample data
        mock_plant = {
            "country": "Denmark",
            "plantName": "Test Plant",
            "id": "1234567"
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"obj": mock_plant}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.get_plant(self.test_plant_id)
        
        # Verify
        self.assertEqual(result, mock_plant)
        mock_post.assert_called_once()
        self.assertTrue(mock_post.call_args.args[0].endswith(f'/panel/getPlantData?plantId={self.test_plant_id}'))

    @patch('requests.Session.post')
    def test_get_device_list(self, mock_post):
        """Test getting device list with pagination."""
        # Mock data for first page
        page1_data = {
            "obj": {
                "datas": [{"sn": "123", "name": "Device1"}],
                "pageCount": 2  # Total 2 pages
            }
        }
        
        # Mock data for second page
        page2_data = {
            "obj": {
                "datas": [{"sn": "456", "name": "Device2"}],
                "pageCount": 2
            }
        }
        
        # Configure mock to return different responses for each call
        mock_response1 = MagicMock()
        mock_response1.json.return_value = page1_data
        mock_response1.raise_for_status.return_value = None
        
        mock_response2 = MagicMock()
        mock_response2.json.return_value = page2_data
        mock_response2.raise_for_status.return_value = None
        
        mock_post.side_effect = [mock_response1, mock_response2]

        # Test default method (MAX devices)
        result = self.growatt.get_device_list(self.test_plant_id)
        
        # Verify
        self.assertEqual(len(result), 2)  # Combined results from both pages
        self.assertEqual(result[0]["sn"], "123")
        self.assertEqual(result[1]["sn"], "456")
        self.assertEqual(mock_post.call_count, 2)  # Called twice for two pages

    @patch('requests.Session.post')
    def test_get_device_list_with_device_type(self, mock_post):
        """Test getting device list with specific device type."""
        # Mock data
        mock_data = {
            "obj": {
                "datas": [{"sn": "123", "name": "MIX Device"}],
                "pageCount": 1
            }
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test with specific endpoint for MIX devices
        # In the real implementation, different device types use different endpoints
        self.growatt.BASE_URL = "https://server.growatt.com"  # Ensure base URL is set
        result = self.growatt.get_devices_by_plant_list(self.test_plant_id)
        
        # Verify
        mock_post.assert_called_once()
        # Verify correct endpoint was used
        self.assertTrue(mock_post.call_args.args[0].endswith('/panel/getDevicesByPlantList'))

    @patch('requests.Session.post')
    def test_get_device_list_with_limit_pages(self, mock_post):
        """Test getting device list with pagination handling."""
        # Test data - create more realistic test data
        total_pages = 3
        devices_per_page = 2
        all_devices = []
        mock_responses = []
        
        # Create mock data for each page with more realistic device data
        for page in range(1, total_pages + 1):
            # Generate unique devices for this page
            page_devices = [
                {
                    "sn": f"DEV{page}{j}",
                    "name": f"Solar Inverter {page}-{j}",
                    "deviceType": "1",
                    "status": "1" if j % 2 == 0 else "0",  # Alternate status for variety
                    "lastUpdateTime": f"2025-05-{j+1:02d} 10:30:00"
                } 
                for j in range(1, devices_per_page + 1)
            ]
            all_devices.extend(page_devices)
            
            # Create response object for this page
            mock_data = {
                "obj": {
                    "datas": page_devices,
                    "pageCount": total_pages,
                    "currPage": page,
                    "totalCount": total_pages * devices_per_page
                }
            }
            
            # Create mock response
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)
        
        # Configure mock to return different responses for each call
        mock_post.side_effect = mock_responses
        
        # Call the method
        result = self.growatt.get_device_list(self.test_plant_id)
        
        # Verify correct number of API calls
        self.assertEqual(mock_post.call_count, total_pages, 
                         f"Should make exactly {total_pages} API calls for pagination")
        
        # Verify correct number of devices returned
        self.assertEqual(len(result), len(all_devices), 
                         f"Should return {len(all_devices)} devices across all pages")
        
        # Verify API calls were made with correct parameters
        for i, call in enumerate(mock_post.call_args_list):
            expected_page = i + 1
            # Check URL
            self.assertTrue(call.args[0].endswith('/device/getMAXList'), 
                           f"Call {i+1} should use correct endpoint")
            # Check POST data
            self.assertEqual(call.kwargs['data']['plantId'], self.test_plant_id, 
                            f"Call {i+1} should use correct plant ID")
            self.assertEqual(int(call.kwargs['data']['currPage']), expected_page, 
                            f"Call {i+1} should request page {expected_page}")
        
        # Verify content of returned devices
        for i, device in enumerate(result):
            self.assertIn("sn", device, f"Device {i+1} should have a serial number")
            self.assertIn("name", device, f"Device {i+1} should have a name")
            self.assertIn("status", device, f"Device {i+1} should have a status")

    @patch('requests.Session.post')
    def test_get_mix_total(self, mock_post):
        """Test getting MIX total measurements."""
        # Sample data
        mock_data = {
            "eselfToday": "7.4",
            "gridPowerTotal": "2743",
            "epvToday": "31.1"
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"obj": mock_data}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.get_mix_total(self.test_plant_id, self.test_mix_sn)
        
        # Verify
        self.assertEqual(result, mock_data)
        mock_post.assert_called_once()
        # Verify data was passed correctly
        self.assertEqual(mock_post.call_args.kwargs['data']['mixSn'], self.test_mix_sn)

    @patch('requests.Session.post')
    def test_get_energy_stats_daily(self, mock_post):
        """Test getting daily energy statistics."""
        # Test date
        test_date = "2025-05-04"
        
        # Sample data
        mock_data = {
            "result": 1,
            "obj": {
                "etouser": "5.2",
                "charts": {"ppv": [1, 2, 3]}
            }
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.get_energy_stats_daily(test_date, self.test_plant_id, self.test_mix_sn)
        
        # Verify
        self.assertEqual(result, mock_data)
        mock_post.assert_called_once()
        # Verify data was passed correctly
        call_data = mock_post.call_args.kwargs['data']
        self.assertEqual(call_data['date'], test_date)
        self.assertEqual(call_data['plantId'], self.test_plant_id)
        self.assertEqual(call_data['mixSn'], self.test_mix_sn)

    @patch('requests.Session.post')
    def test_get_fault_logs(self, mock_post):
        """Test getting fault logs."""
        # Sample data
        mock_data = {
            "result": 1,
            "obj": {
                "pageNum": 1,
                "count": 1,
                "datas": [
                    {
                        "deviceSn": "TEST123",
                        "deviceName": "Inverter",
                        "errorMsg": "Test error",
                        "happenTime": "2025-05-04 14:30:22"
                    }
                ]
            }
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.get_fault_logs(
            self.test_plant_id,
            date="2025-05-04",
            device_sn="TEST123",
            page_num=1
        )
        
        # Verify
        self.assertEqual(result, mock_data)
        mock_post.assert_called_once()
        # Verify correct data was passed
        call_data = mock_post.call_args.kwargs['data']
        self.assertEqual(call_data['date'], "2025-05-04")
        self.assertEqual(call_data['deviceSn'], "TEST123")
        self.assertEqual(call_data['plantId'], self.test_plant_id)

    @patch('requests.Session.post')
    def test_get_weekly_battery_stats(self, mock_post):
        """Test getting weekly battery statistics."""
        # Sample data
        mock_data = {
            "result": 1,
            "obj": {
                "date": "2025-05-04",
                "cdsTitle": ["2025-04-28", "2025-04-29", "2025-04-30", "2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04"],
                "batType": 1,
                "socChart": {"soc": [90, 85, 92, 88, 95, 91, 89]}
            }
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test
        result = self.growatt.get_weekly_battery_stats(self.test_plant_id, self.test_mix_sn)
        
        # Verify
        self.assertEqual(result, mock_data)
        mock_post.assert_called_once()
        # Verify correct data was passed
        call_data = mock_post.call_args.kwargs['data']
        self.assertEqual(call_data['plantId'], self.test_plant_id)
        self.assertEqual(call_data['mixSn'], self.test_mix_sn)

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_all_integrated_functions(self, mock_get, mock_post):
        """Test multiple Growatt API functions working together in an integrated flow."""
        # Set up mock responses for each API call in the flow
        
        # 1. Login response
        login_response = MagicMock()
        login_response.json.return_value = {"result": 1}
        login_response.raise_for_status.return_value = None
        
        # 2. Plants list response
        plants_response = MagicMock()
        plants_response.json.return_value = [
            {"id": self.test_plant_id, "plantName": "Test Plant", "timezone": "1"}
        ]
        plants_response.raise_for_status.return_value = None
        
        # 3. Plant details response
        plant_details_response = MagicMock()
        plant_details_response.json.return_value = {
            "obj": {
                "id": self.test_plant_id,
                "plantName": "Test Plant",
                "country": "Denmark",
                "nominalPower": "5000"
            }
        }
        plant_details_response.raise_for_status.return_value = None
        
        # 4. Devices list response
        devices_response = MagicMock()
        devices_response.json.return_value = {
            "obj": {
                "datas": [
                    {"sn": self.test_mix_sn, "name": "Test MIX Device", "status": "1"}
                ],
                "pageCount": 1,
                "currPage": 1
            }
        }
        devices_response.raise_for_status.return_value = None
        
        # 5. Device details response
        device_details_response = MagicMock()
        device_details_response.json.return_value = {
            "obj": {
                "eselfToday": "7.4",
                "gridPowerTotal": "2743",
                "epvToday": "31.1"
            }
        }
        device_details_response.raise_for_status.return_value = None
        
        # 6. Logout response
        logout_response = MagicMock()
        logout_response.status_code = 302  # Redirect after successful logout
        
        # Configure mocks to return our prepared responses in sequence
        mock_post.side_effect = [
            login_response,      # login
            plants_response,     # get_plants
            plant_details_response,  # get_plant
            devices_response,    # get_device_list
            device_details_response  # get_mix_total
        ]
        mock_get.return_value = logout_response  # logout
        
        # Execute the full flow of API operations
        
        # 1. Login
        login_result = self.growatt.login(self.test_username, self.test_password)
        self.assertTrue(login_result)
        self.assertTrue(self.growatt.is_logged_in)
        
        # 2. Get plants
        plants = self.growatt.get_plants()
        self.assertEqual(len(plants), 1)
        self.assertEqual(plants[0]["id"], self.test_plant_id)
        
        # 3. Get specific plant details
        plant = self.growatt.get_plant(self.test_plant_id)
        self.assertEqual(plant["id"], self.test_plant_id)
        self.assertEqual(plant["country"], "Denmark")
        
        # 4. Get devices for the plant
        devices = self.growatt.get_device_list(self.test_plant_id)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["sn"], self.test_mix_sn)
        
        # 5. Get details for specific device
        device_details = self.growatt.get_mix_total(self.test_plant_id, self.test_mix_sn)
        self.assertEqual(device_details["epvToday"], "31.1")
        self.assertEqual(device_details["gridPowerTotal"], "2743")
        
        # 6. Logout
        logout_result = self.growatt.logout()
        self.assertTrue(logout_result)
        self.assertFalse(self.growatt.is_logged_in)
        
        # Verify correct sequence and number of API calls
        self.assertEqual(mock_post.call_count, 5)
        self.assertEqual(mock_get.call_count, 1)


if __name__ == '__main__':
    unittest.main()