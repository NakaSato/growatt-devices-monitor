import requests
import re
import hashlib
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from urllib.parse import quote

# Configure logging
logger = logging.getLogger(__name__)

class Growatt:

    def __init__(self):
        self.BASE_URL = "https://server.growatt.com"  # Default URL
        # Uncomment the following line to use the alternate URL
        # self.BASE_URL = "https://openapi.growatt.com"
        self.session = requests.Session()
        self.is_logged_in = False

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

        try:
            res = self.session.post(
                f"{self.BASE_URL}/login",
                data={
                    "account": username,
                    "password": "",
                    "validateCode": "",
                    "isReadPact": 1,
                    "passwordCrc": self._hash_password(self.password)
                },
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                timeout=30  # Add a timeout to prevent hanging requests
            )
            
            # Raise for HTTP errors to be caught below
            res.raise_for_status()

            try:
                json_res = res.json()
                # Log the response for debugging
                print(f"Login response: {json_res}")
                
                if json_res.get("result") == 1:  # Assuming result=1 indicates success
                    self.is_logged_in = True
                    return True
                else:
                    self.is_logged_in = False
                    error_msg = json_res.get("msg", "Unknown error")
                    print(f"Login failed with error: {error_msg}")
                    return False
            except json.JSONDecodeError as e:
                self.is_logged_in = False
                print(f"JSON decode error during login: {str(e)}, Response: {res.text[:200]}")
                raise ValueError(f"Invalid response received during login: {res.text[:200]}")
        except requests.exceptions.RequestException as e:
            self.is_logged_in = False
            print(f"Request error during login: {str(e)}")
            raise ValueError(f"Request failed during login: {str(e)}")

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
            Example:
                [
                    {
                        'timezone': '1',
                        'id': '1234567',
                        'plantName': 'name'
                    },
                    ...
                ]
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
            Example:
                {
                    'country': 'Denmark',
                    'formulaCo2': '0.0',
                    'accountName': 'example@example.com',
                    'city': 'Sample City',
                    'timezone': '2',
                    'co2': '1234',
                    'creatDate': '2023-01-01',
                    'formulaCoal': '0.0',
                    'designCompany': '0',
                    'fixedPowerPrice': '1.2',
                    'id': '123456',
                    'lat': '55.000',
                    'valleyPeriodPrice': '1.0',
                    'tempType': '0',
                    'lng': '9.000',
                    'locationImg': 'null',
                    'tree': '100',
                    'peakPeriodPrice': '1.3',
                    'installMap': '',
                    'plantType': '0',
                    'nominalPower': '5000',
                    'formulaMoney': '0',
                    'formulaTree': '0.0',
                    'plantNmi': '',
                    'flatPeriodPrice': '1.1',
                    'eTotal': '5000.0',
                    'plantImg': '123456_image.jpg',
                    'isShare': 'false',
                    'coal': '1000.0',
                    'moneyUnit': 'usd',
                    'plantName': 'Sample Plant',
                    'moneyUnitText': 'USD'
                }
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
            list: A dictionary containing detailed plant information.
            Example:
                [['OICUJHP1PX', 'OICUJHP1PX', '0']]
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
            list: A dictionary containing total mix information.
            Example:
                {
                "eselfToday": "7.4",
                "gridPowerTotal": "2743",
                "eselfTotal": "3428",
                "elocalLoadToday": "12.6",
                "gridPowerToday": "5.2",
                "elocalLoadTotal": "6171",
                "eexTotal": "0",
                "photovoltaicRevenueToday": "37.3",
                "eexToday": "0",
                "etoGridToday": "18.2",
                "edischarge1Total": "1600.5",
                "photovoltaicRevenueTotal": "7338.4",
                "unit": "kr",
                "edischarge1Today": "0.4",
                "epvToday": "31.1",
                "epvTotal": "6115.3",
                "etogridTotal": "2568.6"
                }
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
            list: A dictionary containing the current status of mix information.
            Example:
                    {
                    "pdisCharge1": 0,
                    "uwSysWorkMode": "5",
                    "pactouser": 0,
                    "vBat": "53.1",
                    "vAc1": "236.7",
                    "priorityChoose": "0",
                    "lost": "mix.status.normal",
                    "pactogrid": 0.34,
                    "pLocalLoad": 0.84,
                    "vPv2": "252.9",
                    "deviceType": "2",
                    "pex": 0,
                    "chargePower": 0,
                    "vPv1": "256.7",
                    "upsVac1": "0",
                    "SOC": "95",
                    "wBatteryType": "1",
                    "pPv2": "615.6",
                    "fAc": "50.02",
                    "vac1": "236.7",
                    "pPv1": "568.4",
                    "storagePpv": "1.18",
                    "upsFac": "0",
                    "ppv": 1.18,
                    "status": "5"
                    }
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

        Example:
        api.get_energy_stats_daily(date="2024-07-28", plantId="1234567", mixSn="ODCUTJF8IFP")

        Returns:
            list: A JSON object that contains periodic data for the given day.
            Example:

        {
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
            }
        }
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

        Example:
        api.get_energy_stats_daily(date="2024-07", plantId="1234567", mixSn="ODCUTJF8IFP")

        Returns:
            list: A JSON object that contains periodic data for the given month.
            Example:

        {
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
            }
        }
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

        Example:
        api.get_energy_stats_daily(year="2024", plantId="1234567", mixSn="ODCUTJF8IFP")


        Returns:
            list: A JSON object that contains periodic data for the given year.
            Example:

        {
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
            }
        }
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

        Example:
        api.get_energy_stats_daily(year="2024", plantId="1234567", mixSn="ODCUTJF8IFP")

        Returns:
            list: A JSON object that contains total periodic data.
            Example:

        {
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
            }
        }
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
        '''
        Fetch the daily charge and discharge of your battery within the last 7 days.

        Parameters:
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            Example:
            {
                "result": 1,
                "obj": {
                    "date": "2024-08-06",
                    "cdsTitle": [
                    "2024-07-31",
                    "2024-08-01",
                    "2024-08-02",
                    "2024-08-03",
                    "2024-08-04",
                    "2024-08-05",
                    "2024-08-06"
                    ],
                    "batType": 1,
                    "socChart": {
                    "soc": [LIST]
                    },
                    "cdsData": {
                    "cd_charge": [LIST],
                    "cd_disCharge": [LIST]
                    }
                }
            }
        '''

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
        '''
        Set inverter data time.

        Parameters:
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Returns:
            Example:

        '''

        data = {
                  "action":"mixSet",    # Parameter set Action
                  "serialNum":mixSn,    # Parameter Serial Number of the inverter
                  "type":"pf_sys_year",    # Parameter set Command Type
                  "param1":datetime.now()    # Parameter 1
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
        Retrieves a list of MAX devices associated with a plant, handling pagination.
        
        This method automatically fetches all pages of device data by checking the total
        page count from the first response.
        
        Args:
            plantId (str): The ID of the plant to retrieve devices for.
            
        Returns:
            dict: A dictionary containing all MAX devices from all pages.
            Example:
                {
                    "result": 1,
                    "obj": {
                        "datas": [
                            {
                                "deviceSn": "MAX123456",
                                "deviceName": "MAX Device 1",
                                ...
                            },
                            ...
                        ],
                        "totalCount": 10
                    }
                }
            
        Raises:
            ValueError: If the API returns an empty or invalid response.
        """
        all_devices = []
        current_page = 1
        total_pages = None
        
        # Ensure we have a valid session before making requests
        if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
            raise ValueError("Not logged in. Please login before fetching device data.")
        
        # Add more detailed user agent and headers to mimic browser behavior
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{self.BASE_URL}/panel/plant/plantDetail?plantId={plantId}"
        }
        
        while total_pages is None or current_page <= total_pages:
            data = {
                "plantId": str(plantId),
                "currPage": current_page,
            }
            
            try:
                print(f"Requesting page {current_page} of MAX devices for plant {plantId}...")
                
                # Try using alternative endpoint path first
                try:
                    url = f"{self.BASE_URL}/device/getMAXList"
                    res = self.session.post(url, data=data, headers=headers, timeout=30)
                    
                    # If this fails with 404, we'll try the alternative endpoint in the except block
                    res.raise_for_status()
                    
                    # Debug response info
                    print(f"Response status code: {res.status_code}")
                    print(f"Response headers: {res.headers}")
                    
                    # Print first 200 chars of response for debugging
                    response_preview = res.text[:200] + ("..." if len(res.text) > 200 else "")
                    print(f"Response body (preview): {response_preview}")
                    
                    # Try to parse JSON response
                    json_res = res.json()
                    
                except re.exceptions.HTTPError as e:
                    if res.status_code == 404:
                        # Try alternative endpoint if primary endpoint returns 404
                        print(f"Primary endpoint returned 404, trying alternative endpoint...")
                        url = f"{self.BASE_URL}/panel/max/getMAXList"
                        res = self.session.post(url, data=data, headers=headers, timeout=30)
                        res.raise_for_status()
                        
                        # Debug info for alternative endpoint
                        print(f"Alternative endpoint response status: {res.status_code}")
                        response_preview = res.text[:200] + ("..." if len(res.text) > 200 else "")
                        print(f"Alternative response body (preview): {response_preview}")
                        
                        json_res = res.json()
                    else:
                        # Re-raise if it's not a 404 error
                        raise

                # Check if the response is empty
                if not json_res:
                    print(f"Warning: Empty JSON response for page {current_page}")
                    break
                
                # Handle case where response is an integer (API error or unexpected response)
                if isinstance(json_res, int):
                    print(f"Warning: Received integer response ({json_res}) instead of expected object for plant {plantId}")
                    # Return empty result in the expected format to avoid len() errors
                    return {
                        "result": 0,
                        "obj": {
                            "datas": [],
                            "totalCount": 0
                        }
                    }
                
                # Handle different response formats:
                # 1. Old format: {"result": 1, "obj": {"datas": [...]}}
                # 2. New format: {"currPage": 1, "pages": 2, "datas": [...]}
                
                if "obj" in json_res:
                    # Old format
                    if "datas" in json_res["obj"]:
                        page_devices = json_res["obj"]["datas"]
                        device_count = len(page_devices)
                        
                        if device_count > 0:
                            all_devices.extend(page_devices)
                            print(f"Retrieved {device_count} devices from page {current_page} for plant {plantId} (old format)")
                        else:
                            print(f"Page {current_page} contains no devices for plant {plantId} (old format)")
                    
                    # Determine total pages from old format
                    if total_pages is None:
                        if "pageCount" in json_res["obj"]:
                            total_pages = int(json_res["obj"]["pageCount"])
                        elif "totalPage" in json_res["obj"]:
                            total_pages = int(json_res["obj"]["totalPage"])
                        elif "totalCount" in json_res["obj"] and "pageSize" in json_res["obj"]:
                            total_count = int(json_res["obj"]["totalCount"])
                            page_size = int(json_res["obj"]["pageSize"])
                            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                        else:
                            total_pages = 1
                            
                        print(f"Total pages: {total_pages} (old format)")
                        
                elif "datas" in json_res:
                    # New format - direct access to datas array
                    page_devices = json_res["datas"]
                    device_count = len(page_devices)
                    
                    if device_count > 0:
                        all_devices.extend(page_devices)
                        print(f"Retrieved {device_count} devices from page {current_page} for plant {plantId} (new format)")
                    else:
                        print(f"Page {current_page} contains no devices for plant {plantId} (new format)")
                    
                    # Determine total pages from new format
                    if total_pages is None:
                        if "pages" in json_res:
                            total_pages = int(json_res["pages"])
                            print(f"Total pages: {total_pages} (new format)")
                        else:
                            total_pages = 1
                            print(f"No pages info, assuming single page (new format)")
                else:
                    print(f"Warning: Unknown response format. Keys: {list(json_res.keys())}")
                    # If we can't determine the format, assume it's a single page
                    if total_pages is None:
                        total_pages = 1
                        print("Assuming single page for unknown format")
                
                # Move to next page
                current_page += 1
                
                # Check if we've processed all pages
                if current_page > total_pages:
                    break
                    
            except re.exceptions.JSONDecodeError as e:
                print(f"JSON decode error for page {current_page}: {str(e)}")
                print(f"Response text (first 300 chars): {res.text[:300]}")
                # If we can't parse the JSON, it might be an HTML login page
                if "<html" in res.text.lower() and "login" in res.text.lower():
                    print("Session may have expired. Response contains HTML login page.")
                    self.is_logged_in = False
                    raise ValueError("Session expired. Please login again.")
                else:
                    raise ValueError(f"Invalid JSON response for page {current_page}: {str(e)}")
            except re.exceptions.RequestException as e:
                print(f"Request error for page {current_page}: {str(e)}")
                raise ValueError(f"Request failed for page {current_page}: {str(e)}")
        
        print(f"Finished retrieving devices. Total devices found: {len(all_devices)}")
        
        # Return in the format that the rest of the code expects
        # We'll maintain the same output structure for compatibility
        return {
            "result": 1,
            "obj": {
                "datas": all_devices,
                "totalCount": len(all_devices)
            }
        }

    def get_weather(self, plantId: str):
        """
        Fetch yearly energy statistics.

        Parameters:
        year (str): The year for the energy statistics in 'YYYY' format.
        plantId (str): The ID of the plant.
        mixSn (str): The serial number of the mix device.

        Example:
        api.get_energy_stats_daily(year="2024", plantId="1234567", mixSn="ODCUTJF8IFP")

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
        
    def get_devices_by_plant_list(self, plantId: str, currPage: int = 1):
        """
        Retrieves a list of all devices associated with a plant.

        Args:
            plantId (str): The ID of the plant to retrieve devices for.
            currPage (int, optional): The page number for pagination. Defaults to 1.


        Returns:
            dict: A dictionary containing detailed information about all devices in the plant.
            Example:
                {
                    "result": 1,
                    "obj": {
                        "totalCount": 5,
                        "mix": [...],
                        "max": [...],
                        "tlx": [...],
                        "inv": [...],
                        "storage": [...],
                        "other devices": [...]
                    }
                }
        """
        if not hasattr(self, 'is_logged_in') or not self.is_logged_in:
            raise ValueError("Not logged in. Please login before fetching device data.")
            
        data = {
            "plantId": str(plantId),
            "currPage": currPage
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{self.BASE_URL}/panel/plant/plantDetail?plantId={plantId}"
        }
        
        try:
            logger.debug(f"Fetching devices for plant {plantId}, page {currPage}")
            res = self.session.post(
                f"{self.BASE_URL}/panel/getDevicesByPlantList", 
                data=data,
                headers=headers,
                timeout=30
            )
            
            # Log response details for debugging
            logger.debug(f"Response status code: {res.status_code}")
            logger.debug(f"Response headers: {res.headers}")
            
            # Check for 500 error
            if res.status_code == 500:
                error_msg = f"Server error (500) when fetching devices for plant {plantId}"
                logger.error(error_msg)
                return {
                    "result": 0,
                    "msg": error_msg,
                    "obj": {
                        "totalCount": 0,
                        "mix": [],
                        "max": [],
                        "tlx": [],
                        "inv": [],
                        "storage": []
                    }
                }
                
            res.raise_for_status()
            
            try:
                json_res = res.json()
                logger.debug(f"Raw devices response for plant {plantId}: {json.dumps(json_res, indent=2)[:500]}...")  # Log first 500 chars
                
                # Handle different response formats
                if not json_res:
                    logger.warning(f"Empty response for plant {plantId}")
                    return {
                        "result": 0,
                        "msg": "Empty response",
                        "obj": {
                            "totalCount": 0,
                            "mix": [],
                            "max": [],
                            "tlx": [],
                            "inv": [],
                            "storage": []
                        }
                    }
                    
                # Ensure we have the expected structure
                if not isinstance(json_res, dict):
                    logger.warning(f"Unexpected response format for plant {plantId}: {type(json_res)}")
                    return {
                        "result": 0,
                        "msg": "Unexpected response format",
                        "obj": {
                            "totalCount": 0,
                            "mix": [],
                            "max": [],
                            "tlx": [],
                            "inv": [],
                            "storage": []
                        }
                    }
                
                # If we have an error in the response
                if 'result' in json_res and json_res.get('result') == 0:
                    error_msg = json_res.get('msg', 'Unknown error')
                    logger.warning(f"API returned error for plant {plantId}: {error_msg}")
                    
                return json_res
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to decode JSON response for plant {plantId}: {str(e)}"
                logger.error(f"{error_msg}. Response text: {res.text[:500]}...")
                raise ValueError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed for plant {plantId}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    def get_fault_logs(self, plantId: str, date: str = None, device_sn: str = "", page_num: int = 1, device_flag: int = 0, fault_type: int = 1):
        """
        Retrieves fault logs for a specific plant.
        
        Args:
            plantId (str): The ID of the plant to retrieve fault logs for.
            date (str, optional): The date for which to retrieve logs in 'YYYY-MM-DD' format. Defaults to current date.
            device_sn (str, optional): Serial number of a specific device. Empty string for all devices.
            page_num (int, optional): Page number for pagination. Defaults to 1.
            device_flag (int, optional): Flag indicating device type (0=all, 1=inverter, etc). Defaults to 0.
            fault_type (int, optional): Type of fault log to retrieve (1=fault, 2=alarm, etc). Defaults to 1.
            
        Returns:
            dict: A dictionary containing fault logs.
            Example:
                {
                    "result": 1,
                    "obj": {
                        "pageNum": 1,
                        "count": 10,
                        "datas": [
                            {
                                "deviceSn": "EXAMPLE123",
                                "deviceName": "Inverter",
                                "errorMsg": "Error description",
                                "happenTime": "2024-04-15 14:30:22"
                            },
                            ...
                        ]
                    }
                }
                
        Raises:
            ValueError: If the API returns an empty or invalid response.
            requests.exceptions.HTTPError: If the HTTP request fails.
        """
        # Use current date if none provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        # Validate inputs
        if not plantId:
            raise ValueError("Plant ID must be provided")
        
        # Prepare request data
        data = {
            "deviceSn": device_sn,
            "date": date,
            "plantId": str(plantId),
            "toPageNum": str(page_num),
            "type": str(fault_type),
            "deviceFlag": str(device_flag)
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        
        # Make API request
        res = self.session.post(f"{self.BASE_URL}/log/getNewPlantFaultLog", data=data, headers=headers)
        res.raise_for_status()
        
        try:
            json_res = res.json()
            
            if not json_res:
                raise ValueError("Empty response received from server")
            return json_res
        except re.exceptions.JSONDecodeError:
            raise ValueError("Invalid JSON response received from server")
    
    # Alias for backward compatibility
    get_plant_fault_logs = get_fault_logs