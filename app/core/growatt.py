# No unused imports
import requests as re
import hashlib
from datetime import datetime

class Growatt:

    def __init__(self):
        self.BASE_URL = "https://server.growatt.com"  # Default URL
        # Uncomment the following line to use the alternate URL
        # self.BASE_URL = "https://openapi.growatt.com"
        self.session = re.Session()
        print("Session: ", re.Session)

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
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
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
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
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
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
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
            "result": 1,
            "obj": {
            "etouser": "5.2",
            "charts": {
            "pex": [LIST],
            "pacToGrid": [LIST],
            "pcharge": [LIST],
            "ppv": [LIST],
            "sysOut": [LIST],
            "pself": [LIST],
            "elocalLoad": [LIST],
            "pdischarge": [LIST],
            "pacToUser": [LIST]
            },
            "eCharge": "25.7",
            "eAcCharge": "18.3",
            "eChargeToday2": "7.4",
            "elocalLoad": "12.6",
            "eChargeToday1": "7.4"
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
                "result": 1,
                "obj": {
                    "date": "2024-08-06",
                    "cdsTitle": [
                    "2024-07-31",
                    "2024-08-01",
                    "2024-08-02",
                    "2024-08-03",
                    "2024-08-04",
                    "2024-08-05",
                    "2024-08-06"
                    ],
                    "batType": 1,
                    "socChart": {
                    "soc": [LIST]
                    },
                    "cdsData": {
                    "cd_charge": [LIST],
                    "cd_disCharge": [LIST]
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
