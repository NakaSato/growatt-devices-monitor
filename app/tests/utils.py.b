import os
from typing import List, Dict, Any, Optional, Union
from flask import current_app
import time
from datetime import datetime
import requests as re
import hashlib

# Login credentials from environment variables (with fallbacks for development)
username = os.environ.get("GROWATT_USERNAME", "enwufttest")
username = os.environ.get("GROWATT_PASSWORD", "enwuft1234")
# GROWATT_USERNAME = os.environ.get("GROWATT_USERNAME", "PWA_solar")
# GROWATT_PASSWORD = os.environ.get("GROWATT_PASSWORD", "123456")

class Growatt:
    def __init__(self):
        self.BASE_URL = "https://server.growatt.com"  # Default URL
        # Uncomment the following line to use the alternate URL
        # self.BASE_URL = "https://openapi.growatt.com"
        self.session = re.Session()

    def _hash_password(self, password: str) -> str:
        """
        Hashes the given password using MD5.

        Args:
            password (str): The plain text password to be hashed.

        Returns:
            str: The MD5 hash of the password.
        """
        return hashlib.md5(password.encode()).hexdigest()

    def login(self, username: str, password: str):
        """
        Logs in the user and saves the session. If already logged in, skips re-login.

        Args:
            username (str): The username for login.
            password (str): The password for login.

        Returns:
            bool: True if login was successful, False otherwise.
        """
        if hasattr(self, 'is_logged_in') and self.is_logged_in:
            return True  # Skip login if already logged in

        self.username = username
        self.password = password

        res = self.session.post(
            f"{self.BASE_URL}/login",
            data={
                "account": username,
                "password": "",
                "validateCode": "",
                "isReadPact": 1,
                "passwordCrc": self._hash_password(self.password)
            },
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        )
        res.raise_for_status()

        try:
            json_res = res.json()
            if json_res.get("result") == 1:  # Assuming result=1 indicates success
                self.is_logged_in = True
                return True
            else:
                self.is_logged_in = False
                return False
        except re.exceptions.JSONDecodeError:
            self.is_logged_in = False
            raise ValueError("Invalid response received during login.")

    def logout(self):
        """
        Logs out the user and clears the session on the server.

        Returns:
            bool: True if logout was successful, False otherwise.
        """
        if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
            print("No active session to log out from.")
            return False  # No active session to log out from

        headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Referer": f"{self.BASE_URL}/index"
        }

        res = self.session.get(f"{self.BASE_URL}/logout", headers=headers, allow_redirects=False)

        # Expect a redirect (302) response for successful logout
        if res.status_code == 302:
            self.is_logged_in = False
            self.session.cookies.clear()  # Clear session cookies
            print("Successfully logged out.")
            return True
        else:
            print(f"Logout failed with status code: {res.status_code}")
            return False

    def get_plants(self):
        """
        Retrieves the list of plants associated with the user.

        Returns:
            list: A list of dictionaries, each containing details about a plant.
        """
        res = self.session.post(f"{self.BASE_URL}/index/getPlantListTitle")
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_plant(self, plantId: str):
        """
        Retrieves specific plant information by plantId.

        Args:
            plantId (str): The ID of the plant to retrieve.

        Returns:
            dict: A dictionary containing detailed plant information.
        """
        res = self.session.post(f"{self.BASE_URL}/panel/getPlantData?plantId={plantId}")
        res.raise_for_status()

        try:
            json_res = res.json()["obj"]

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_mix_ids(self, plantId: str):
        """
        Retrieves the MIX id's by plantId.

        Args:
            plantId (str): The ID of the MIX id's to retrieve.

        Returns:
            list: A list containing MIX IDs.
        """
        res = self.session.post(f"{self.BASE_URL}/panel/getDevicesByPlant?plantId={plantId}")
        res.raise_for_status()

        try:
            json_res = res.json()['obj']["mix"]

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_mix_total(self, plantId: str, mixSn: str):
        """
        Retrieves the total measurements from specific MIX.

        Args:
            plantId (str): The ID of the plant.
            mixSn (str): The ID of the MIX.

        Returns:
            dict: A dictionary containing total mix information.
        """
        data = {
            'mixSn': str(mixSn),
        }
        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXTotalData?plantId={plantId}", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()["obj"]

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_mix_status(self, plantId: str, mixSn: str):
        """
        Retrieves the current status of measurements from specific MIX.

        Args:
            plantId (str): The ID of the plant.
            mixSn (str): The ID of the MIX.

        Returns:
            dict: A dictionary containing the current status of mix information.
        """
        data = {
            'mixSn': mixSn
        }

        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXStatusData?plantId={plantId}", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()["obj"]

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_energy_stats_daily(self, date: str, plantId: str, mixSn: str):
        """
        Fetch daily energy statistics.

        Parameters:
        date (str): The date for the energy statistics in 'YYYY-MM-DD' format.
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            dict: A JSON object that contains periodic data for the given day.
        """
        data = {
            "date": date,
            "plantId": str(plantId),
            "mixSn": mixSn
        }

        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXEnergyDayChart", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_energy_stats_monthly(self, date: str, plantId: str, mixSn: str):
        """
        Fetch monthly energy statistics.

        Parameters:
        date (str): The date for the energy statistics in 'YYYY-MM' format.
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            dict: A JSON object that contains periodic data for the given month.
        """
        data = {
            "date": date,
            "plantId": str(plantId),
            "mixSn": mixSn
        }

        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXEnergyMonthChart", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_energy_stats_yearly(self, year: str, plantId: str, mixSn: str):
        """
        Fetch yearly energy statistics.

        Parameters:
        year (str): The year for the energy statistics in 'YYYY' format.
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            dict: A JSON object that contains periodic data for the given year.
        """
        data = {
            "year": year,
            "plantId": str(plantId),
            "mixSn": mixSn
        }

        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXEnergyYearChart", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_energy_stats_total(self, year: str, plantId: str, mixSn: str):
        """
        Fetch total energy statistics.

        Parameters:
        year (str): The year for the total energy statistics in 'YYYY' format.
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            dict: A JSON object that contains total periodic data.
        """
        data = {
            "year": year,
            "plantId": str(plantId),
            "mixSn": mixSn
        }

        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXEnergyTotalChart", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_weekly_battery_stats(self, plantId: str, mixSn: str):
        """
        Fetch the daily charge and discharge of your battery within the last 7 days.

        Parameters:
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            dict: A JSON object containing battery stats for the last 7 days.
        """
        data = {
            "plantId": plantId,
            "mixSn": mixSn
        }

        res = self.session.post(f"{self.BASE_URL}/panel/mix/getMIXBatChart", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def post_mix_ac_discharge_time_period_now(self, plantId: str, mixSn: str):
        """
        Set inverter data time.

        Parameters:
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            dict: Response from the server after setting the time.
        """
        data = {
              "action": "mixSet",    # Parameter set Action
              "serialNum": mixSn,    # Parameter Serial Number of the inverter
              "type": "pf_sys_year",    # Parameter set Command Type
              "param1": datetime.now()    # Parameter 1
            }

        res = self.session.post(f"{self.BASE_URL}/tcpSet.do", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_device_list(self, plantId: str):
        """
        Get list of devices for a plant.

        Parameters:
        plantId (str): The ID of the plant.

        Returns:
            dict: Information about devices in the plant.
        """
        data = {
            "plantId": str(plantId),
            "currPage": 1,
        }

        res = self.session.post(f"{self.BASE_URL}/device/getMAXList", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")

    def get_weather(self, plantId: str):
        """
        Get weather information for a plant.

        Parameters:
        plantId (str): The ID of the plant.

        Returns:
            dict: Weather information for the plant.
        """
        data = {
            "plantId": str(plantId),
            "currPage": 1,
        }

        res = self.session.post(f"{self.BASE_URL}/device/getEnvList", data=data)
        res.raise_for_status()

        try:
            json_res = res.json()

            if not json_res:
                raise ValueError("Empty response. Please ensure you are logged in.")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid response received. Please ensure you are logged in.")
# Define a session manager class to work with the Growatt API
class GrowattSessionManager:
    def __init__(self):
        self.api = Growatt()
        self.last_login_time = 0
        # Session timeout in seconds (15 minutes)
        self.SESSION_TIMEOUT = 15 * 60
        self.GROWATT_USERNAME = os.environ.get("GROWATT_USERNAME", "enwufttest")
        self.GROWATT_PASSWORD = os.environ.get("GROWATT_PASSWORD", "enwuft1234")

    def is_session_valid(self) -> bool:
        """
        Check if the current session is valid based on timeout.
        
        Returns:
            bool: True if session is valid, False otherwise
        """
        # If the API isn't logged in yet, return False
        if not hasattr(self.api, 'is_logged_in') or not self.api.is_logged_in:
            return False
            
        # Check if session has timed out
        current_time = time.time()
        if current_time - self.last_login_time > self.SESSION_TIMEOUT:
            current_app.logger.info("Session has timed out")
            return False
            
        return True

    def ensure_login(self) -> Dict[str, Any]:
        """
        Ensure the API session is active by checking validity and logging in if needed.
        
        Returns:
            Dict[str, Any]: Login status information
        """
        if not self.is_session_valid():
            current_app.logger.info("Session not valid, performing fresh login")
            return self.get_access_api()
        
        current_app.logger.debug("Using existing session")
        return {"success": True, "message": "Using existing session"}

    def get_access_api(self) -> Dict[str, Any]:
        """
        Login to the Growatt API using credentials.
        This is the only function that should call the actual login API.
        
        Returns:
            Dict[str, Any]: Raw API response containing login information
        """
        try:
            # Perform new login - the only place where login API is called
            login_result = self.api.login(self.GROWATT_USERNAME, self.GROWATT_PASSWORD)
            current_app.logger.info(f"\033[44m\033[97mLogin attempt result: {login_result}\033[0m")
            
            if login_result:
                # Update the last login time
                self.last_login_time = time.time()
                current_app.logger.info("\033[42m\033[97mSuccessfully logged in to Growatt API\033[0m")
                
                # Return the actual login result from the API
                return {"success": True, "message": "Successfully logged in"}
            else:
                current_app.logger.warning("\033[41m\033[97mLogin failed with invalid credentials\033[0m")
                return {
                    "success": False, 
                    "message": "Authentication failed: Invalid credentials",
                    "code": "INVALID_CREDENTIALS",
                    "ui_message": "Your username or password is incorrect. Please check your credentials."
                }
        except Exception as e:
            current_app.logger.error(f"\033[41m\033[97mError logging in to Growatt API: {e}\033[0m")
            
            error_message = str(e)
            error_code = "API_ERROR"
            ui_message = "Could not connect to Growatt service."
            
            if "timeout" in error_message.lower():
                error_code = "TIMEOUT"
                ui_message = "Connection to Growatt timed out. Please try again later."
            elif "connection" in error_message.lower():
                error_code = "CONNECTION_ERROR"
                ui_message = "Could not connect to Growatt servers. Please check your internet connection."
                
            return {
                "success": False, 
                "message": f"Authentication failed: {error_message}",
                "code": error_code,
                "ui_message": ui_message
            }

    def get_logout(self) -> Dict[str, Any]:
        """
        Logout/sign out from the Growatt API.

        Returns:
            Dict[str, Any]: Dictionary containing logout status
        """
        try:
            # Only attempt logout if we believe we're logged in
            if hasattr(self.api, 'is_logged_in') and self.api.is_logged_in:
                logout_result = self.api.logout()
                
                if logout_result:
                    current_app.logger.info("\033[42m\033[97mLogged out from Growatt API\033[0m")
                    return {"success": True, "message": "Logout successful"}
                else:
                    current_app.logger.warning("\033[43m\033[30mLogout attempt returned False\033[0m")
                    return {"success": False, "message": "Logout failed: Server rejected request"}
            else:
                current_app.logger.info("No active session to log out from")
                return {"success": True, "message": "No active session to log out from", "redirect": "/"}
        except Exception as e:
            current_app.logger.error(f"Error logging out from Growatt API: {e}")
            return {"success": False, "message": f"Logout failed: {str(e)}"}

    def get_plants(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of plants from the Growatt API.

        Returns:
            List[Dict[str, Any]]: List of plant data dictionaries with authentication status
        """
        try:
            # Always perform a fresh login before making API call
            login_status = self.ensure_login()
            if not login_status.get("success", False):
                current_app.logger.error("Failed to establish session before fetching plants")
                return [{"error": "Authentication failed", "code": "AUTH_ERROR", 
                        "ui_message": "Please log in to access your plant data",
                        "authenticated": False}]
                
            # Call the API object's get_plants method
            plants_data = self.api.get_plants()
            
            if not plants_data:
                current_app.logger.warning("No plants data retrieved or empty response")
                return [{"error": "No plants found", "code": "NO_PLANTS", 
                        "ui_message": "No solar plants found for this account",
                        "authenticated": True}]
                
            if isinstance(plants_data, list):
                for plant in plants_data:
                    plant['authenticated'] = True
                current_app.logger.info(f"\033[92mRetrieved {len(plants_data)} plants\033[0m")
                return plants_data
            else:
                current_app.logger.error(f"Unexpected plants data format: {type(plants_data)}")
                return [{"error": "Unexpected response format", "code": "INVALID_FORMAT", 
                        "ui_message": "Received unexpected data format from Growatt",
                        "authenticated": True}]
        except Exception as e:
            current_app.logger.error(f"\033[41m\033[97mError in API request get_plants: {e}\033[0m")
            
            return [{"error": str(e), "code": "API_ERROR", 
                    "ui_message": "An error occurred while fetching plant data. Please try logging in again.",
                    "authenticated": False}]

    def get_plant_ids(self) -> List[str]:
        """
        Fetch the plant IDs associated with the logged-in user.

        Returns:
            List[str]: List of plant IDs
        """
        
        try:
            # Ensure session is valid
            self.ensure_login()
            
            plants = self.api.get_plants()

            if isinstance(plants, list):
                plant_ids = [plant['id'] for plant in plants if 'id' in plant]
                current_app.logger.debug(f"Retrieved {len(plant_ids)} plant IDs")
                return plant_ids

            return []
        except Exception as e:
            current_app.logger.error(f"Error in API request get_plant_ids: {e}")
            return [{"error": str(e), "code": "API_ERROR", 
                    "ui_message": "An error occurred while fetching plant IDs.",
                    "authenticated": False}]

    def get_plant_by_id(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the details of a specific plant by its ID from the Growatt API.

        Args:
            plant_id (str): The ID of the plant to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Plant data dictionary or None if not found
        """

        try:
            # Ensure session is valid
            self.ensure_login()
            
            plants = self.api.get_plants()

            if isinstance(plants, list):
                for plant in plants:
                    if plant.get('id') == plant_id:
                        return plant
                
                current_app.logger.warning(f"No plant found with ID: {plant_id}")

            return None
        except Exception as e:
            current_app.logger.error(f"Error in API request get_plant_by_id: {e}")
            return None

    def get_devices_for_plant(self, plant_id: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch the list of devices for a specific plant by its ID from the Growatt API.
        
        Args:
            plant_id (str): The ID of the plant to retrieve devices for
            
        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: Devices data
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            devices = self.api.get_device_list(plant_id)
            current_app.logger.debug(f"Retrieved devices for plant ID {plant_id}")
            return devices
        except Exception as e:
            current_app.logger.error(f"Error fetching devices for plant ID {plant_id}: {e}")
            return [{"error": str(e), "code": "API_ERROR", 
                    "ui_message": "An error occurred while fetching devices for this plant.",
                    "authenticated": False}]

    def get_weather_list(self, plant_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch weather data for a specific plant or all plants.

        Args:
            plant_id (Optional[str]): The ID of the plant to retrieve weather for,
                                    or None to get all weather data
            
        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: Weather data
        """

        try:
            # Ensure session is valid
            self.ensure_login()
            
            weather_list = self.api.get_weather(plantId=plant_id or "")

            if plant_id is not None and isinstance(weather_list, list):
                for weather in weather_list:
                    if weather.get('id') == plant_id:
                        current_app.logger.debug(f"Retrieved weather for plant ID {plant_id}")
                        return weather
                # If plant_id was specified but not found in results
                return {"warning": f"No weather data found for plant ID {plant_id}", "authenticated": True}

            current_app.logger.debug(f"Retrieved weather data for all plants")
            return weather_list
        except Exception as e:
            current_app.logger.error(f"Error in API request get_weather_list: {e}")
            return [{"error": str(e), "code": "API_ERROR", 
                    "ui_message": "An error occurred while fetching weather data.",
                    "authenticated": False}]

    def get_plant_details(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific plant by its ID.

        Args:
            plant_id (str): The ID of the plant to retrieve details for
            
        Returns:
            Optional[Dict[str, Any]]: Detailed plant data or None if not found/error
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            plant_details = self.api.get_plant(plant_id)
            current_app.logger.debug(f"Retrieved detailed info for plant ID {plant_id}")
            return plant_details
        except Exception as e:
            current_app.logger.error(f"Error fetching plant details for ID {plant_id}: {e}")
            return None

    def get_mix_ids_for_plant(self, plant_id: str) -> List[List[str]]:
        """
        Fetch the MIX IDs for a specific plant.
        
        Args:
            plant_id (str): The ID of the plant to retrieve MIX IDs for
            
        Returns:
            List[List[str]]: List of MIX ID data in format [['ID', 'Name', 'Status']]
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            mix_ids = self.api.get_mix_ids(plant_id)
            current_app.logger.debug(f"Retrieved {len(mix_ids)} MIX IDs for plant ID {plant_id}")
            return mix_ids
        except Exception as e:
            current_app.logger.error(f"Error fetching MIX IDs for plant ID {plant_id}: {e}")
            return []

    def get_mix_status(self, plant_id: str, mix_sn: str) -> Dict[str, Any]:
        """
        Fetch the current status of a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            
        Returns:
            Dict[str, Any]: Current status data for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            mix_status = self.api.get_mix_status(plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved status for MIX {mix_sn} on plant ID {plant_id}")
            return mix_status
        except Exception as e:
            current_app.logger.error(f"Error fetching MIX status for plant ID {plant_id}, MIX SN {mix_sn}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve MIX status"}

    def get_mix_total(self, plant_id: str, mix_sn: str) -> Dict[str, Any]:
        """
        Fetch the total measurements from a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            
        Returns:
            Dict[str, Any]: Total measurement data for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            mix_total = self.api.get_mix_total(plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved total measurements for MIX {mix_sn} on plant ID {plant_id}")
            return mix_total
        except Exception as e:
            current_app.logger.error(f"Error fetching MIX total for plant ID {plant_id}, MIX SN {mix_sn}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve MIX total data"}

    def get_mix_daily_energy(self, plant_id: str, mix_sn: str, date: str = None) -> Dict[str, Any]:
        """
        Fetch daily energy statistics for a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
            
        Returns:
            Dict[str, Any]: Daily energy statistics for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            # Use today's date if not specified
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
                
            energy_stats = self.api.get_energy_stats_daily(date, plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved daily energy stats for MIX {mix_sn} on plant ID {plant_id} for date {date}")
            return energy_stats
        except Exception as e:
            current_app.logger.error(f"Error fetching daily energy stats for plant ID {plant_id}, MIX SN {mix_sn}, date {date}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve daily energy statistics"}

    def get_mix_monthly_energy(self, plant_id: str, mix_sn: str, month: str = None) -> Dict[str, Any]:
        """
        Fetch monthly energy statistics for a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            month (str, optional): Month in YYYY-MM format. Defaults to current month.
            
        Returns:
            Dict[str, Any]: Monthly energy statistics for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            # Use current month if not specified
            if month is None:
                month = datetime.now().strftime("%Y-%m")
                
            energy_stats = self.api.get_energy_stats_monthly(month, plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved monthly energy stats for MIX {mix_sn} on plant ID {plant_id} for month {month}")
            return energy_stats
        except Exception as e:
            current_app.logger.error(f"Error fetching monthly energy stats for plant ID {plant_id}, MIX SN {mix_sn}, month {month}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve monthly energy statistics"}

    def get_mix_yearly_energy(self, plant_id: str, mix_sn: str, year: str = None) -> Dict[str, Any]:
        """
        Fetch yearly energy statistics for a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            year (str, optional): Year in YYYY format. Defaults to current year.
            
        Returns:
            Dict[str, Any]: Yearly energy statistics for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            # Use current year if not specified
            if year is None:
                year = datetime.now().strftime("%Y")
                
            energy_stats = self.api.get_energy_stats_yearly(year, plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved yearly energy stats for MIX {mix_sn} on plant ID {plant_id} for year {year}")
            return energy_stats
        except Exception as e:
            current_app.logger.error(f"Error fetching yearly energy stats for plant ID {plant_id}, MIX SN {mix_sn}, year {year}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve yearly energy statistics"}

    def get_mix_total_energy(self, plant_id: str, mix_sn: str, year: str = None) -> Dict[str, Any]:
        """
        Fetch total energy statistics for a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            year (str, optional): Year in YYYY format for stats. Defaults to current year.
            
        Returns:
            Dict[str, Any]: Total energy statistics for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            # Use current year if not specified
            if year is None:
                year = datetime.now().strftime("%Y")
                
            energy_stats = self.api.get_energy_stats_total(year, plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved total energy stats for MIX {mix_sn} on plant ID {plant_id}")
            return energy_stats
        except Exception as e:
            current_app.logger.error(f"Error fetching total energy stats for plant ID {plant_id}, MIX SN {mix_sn}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve total energy statistics"}

    def get_mix_battery_stats(self, plant_id: str, mix_sn: str) -> Dict[str, Any]:
        """
        Fetch weekly battery statistics for a specific MIX device.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            
        Returns:
            Dict[str, Any]: Weekly battery statistics for the MIX device
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            battery_stats = self.api.get_weekly_battery_stats(plant_id, mix_sn)
            current_app.logger.debug(f"Retrieved weekly battery stats for MIX {mix_sn} on plant ID {plant_id}")
            return battery_stats
        except Exception as e:
            current_app.logger.error(f"Error fetching battery stats for plant ID {plant_id}, MIX SN {mix_sn}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to retrieve battery statistics"}

    def sync_mix_time(self, plant_id: str, mix_sn: str) -> Dict[str, Any]:
        """
        Synchronize the time on a MIX device with the current time.
        
        Args:
            plant_id (str): The ID of the plant
            mix_sn (str): The serial number of the MIX device
            
        Returns:
            Dict[str, Any]: Result of the time synchronization operation
        """
        try:
            # Ensure session is valid
            self.ensure_login()
            
            sync_result = self.api.post_mix_ac_discharge_time_period_now(plant_id, mix_sn)
            current_app.logger.debug(f"Synchronized time for MIX {mix_sn} on plant ID {plant_id}")
            return sync_result
        except Exception as e:
            current_app.logger.error(f"Error syncing time for plant ID {plant_id}, MIX SN {mix_sn}: {e}")
            return {"error": str(e), "code": "API_ERROR", "ui_message": "Failed to synchronize device time"}

# Create a singleton instance of the session manager
growatt_session = GrowattSessionManager()
