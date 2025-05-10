#!/usr/bin/env python3
"""
Inverter Data Collector

A script to collect detailed inverter information and historical data from
the Growatt API and store it in the PostgreSQL database.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

# Add parent directory to path so we can import from app
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Import from the app
from app.config import Config
from app.database import get_db_connection
from app.core.growatt import Growatt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'inverter_data_collector.log'))
    ]
)
logger = logging.getLogger("inverter_data_collector")

def ensure_logs_dir():
    """Ensure logs directory exists"""
    logs_dir = os.path.join(parent_dir, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        logger.info(f"Created logs directory at {logs_dir}")

def ensure_database_tables():
    """
    Ensure the necessary database tables exist
    
    Returns:
        bool: True if tables were created/verified successfully
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create inverter_details table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inverter_details (
                    id SERIAL PRIMARY KEY,
                    serial_number TEXT NOT NULL,
                    plant_id TEXT NOT NULL,
                    model TEXT,
                    firmware_version TEXT,
                    hardware_version TEXT,
                    nominal_power REAL,
                    max_ac_power REAL,
                    max_dc_power REAL,
                    efficiency REAL,
                    temperature REAL,
                    dc_voltage_1 REAL,
                    dc_current_1 REAL,
                    dc_power_1 REAL,
                    dc_voltage_2 REAL,
                    dc_current_2 REAL,
                    dc_power_2 REAL,
                    ac_voltage REAL,
                    ac_current REAL,
                    ac_frequency REAL,
                    ac_power REAL,
                    daily_energy REAL,
                    total_energy REAL,
                    operating_time INTEGER,
                    operating_state TEXT,
                    last_update_time TIMESTAMP,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_data JSONB,
                    FOREIGN KEY (serial_number) REFERENCES devices (serial_number),
                    FOREIGN KEY (plant_id) REFERENCES plants (id),
                    UNIQUE(serial_number, collected_at)
                )
            ''')
            
            # Create inverter_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inverter_history (
                    id SERIAL PRIMARY KEY,
                    serial_number TEXT NOT NULL,
                    plant_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    dc_voltage_1 REAL,
                    dc_current_1 REAL,
                    dc_power_1 REAL,
                    dc_voltage_2 REAL,
                    dc_current_2 REAL,
                    dc_power_2 REAL,
                    ac_voltage REAL,
                    ac_current REAL,
                    ac_frequency REAL,
                    ac_power REAL,
                    temperature REAL,
                    energy REAL,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (serial_number) REFERENCES devices (serial_number),
                    FOREIGN KEY (plant_id) REFERENCES plants (id),
                    UNIQUE(serial_number, timestamp)
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inverter_details_sn ON inverter_details(serial_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inverter_details_plant ON inverter_details(plant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inverter_history_sn ON inverter_history(serial_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inverter_history_plant ON inverter_history(plant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inverter_history_time ON inverter_history(timestamp)')
            
            conn.commit()
            logger.info("Database tables for inverter data verified/created successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error ensuring database tables: {str(e)}")
        return False

class InverterDataCollector:
    """Collects inverter details and history data from the Growatt API and stores it in the database"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        Initialize the inverter data collector
        
        Args:
            server_url: Base URL of the Growatt monitoring API
        """
        self.server_url = server_url
        self.growatt_api = Growatt()
        self.is_authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with the Growatt API
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Login to the Growatt API
            login_result = self.growatt_api.login(Config.GROWATT_USERNAME, Config.GROWATT_PASSWORD)
            
            if login_result and self.growatt_api.is_logged_in:
                self.is_authenticated = True
                logger.info("Authentication with Growatt API successful")
                return True
            else:
                logger.error("Authentication with Growatt API failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
    
    def get_plants(self) -> List[Dict[str, Any]]:
        """
        Get all plants from the Growatt API
        
        Returns:
            List[Dict[str, Any]]: List of plant data dictionaries
        """
        plants = []
        
        try:
            # Get plant list from API
            plant_list = self.growatt_api.get_plants()
            
            if plant_list and isinstance(plant_list, list):
                plants = plant_list
                logger.info(f"Successfully fetched {len(plants)} plants from Growatt API")
            else:
                logger.warning("No plants returned from the Growatt API")
            
            return plants
            
        except Exception as e:
            logger.error(f"Error fetching plants: {str(e)}")
            return []
    
    def get_devices_for_plant(self, plant_id: str) -> List[Dict[str, Any]]:
        """
        Get all devices for a specific plant
        
        Args:
            plant_id: Plant ID to get devices for
            
        Returns:
            List[Dict[str, Any]]: List of device data dictionaries
        """
        devices = []
        
        try:
            # Get devices for the plant
            plant_devices = self.growatt_api.get_devices_by_plant_list(plantId=plant_id)
            
            if plant_devices and isinstance(plant_devices, dict) and "obj" in plant_devices:
                # Check structure of response for debugging
                logger.debug(f"Device response structure: {list(plant_devices.keys())}")
                obj = plant_devices["obj"]
                logger.debug(f"Device obj structure: {list(obj.keys())}")
                
                # Extract devices from different device type arrays
                all_devices = []
                
                # The API returns devices categorized by type (mix, inv, tlx, max, etc.)
                for device_type_key in ["mix", "inv", "tlx", "max", "storage", "datas"]:
                    if device_type_key in obj and isinstance(obj[device_type_key], list):
                        type_devices = obj[device_type_key]
                        logger.debug(f"Found {len(type_devices)} devices of type {device_type_key}")
                        
                        # Print the first device structure if available
                        if type_devices and len(type_devices) > 0:
                            first_device = type_devices[0]
                            logger.debug(f"Sample device structure for {device_type_key}: {list(first_device.keys())}")
                            
                            # Map fields for consistent structure
                            mapped_devices = []
                            for device in type_devices:
                                # Different device types use different field names
                                # Map them to a consistent structure
                                mapped_device = {
                                    "deviceSn": device.get("sn", device.get("deviceSn", "")),
                                    "plantId": plant_id,
                                    "deviceType": device_type_key,
                                    "deviceTypeName": device.get("deviceTypeName", device.get("type", device_type_key)),
                                    "deviceAilas": device.get("alias", device.get("deviceAilas", "")),
                                    "nominalPower": device.get("nominalPower", 0),
                                    # Include all original fields for reference
                                    **device
                                }
                                mapped_devices.append(mapped_device)
                            
                            all_devices.extend(mapped_devices)
                
                # If we found devices in sub-arrays, use those
                if all_devices:
                    devices = all_devices
                else:
                    # Fallback to direct "datas" array if present
                    devices = obj.get("datas", [])
                
                logger.info(f"Successfully fetched {len(devices)} devices for plant {plant_id}")
            else:
                logger.warning(f"No devices returned for plant {plant_id}")
            
            return devices
            
        except Exception as e:
            logger.error(f"Error fetching devices for plant {plant_id}: {str(e)}")
            return []
    
    def get_inverter_data(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed data for an inverter
        
        Args:
            device: Device dictionary containing basic device info
            
        Returns:
            Dict[str, Any]: Detailed inverter data
        """
        try:
            device_sn = device.get("deviceSn", "")
            plant_id = device.get("plantId", "")
            device_type = device.get("deviceType", "")
            device_type_name = device.get("deviceTypeName", "")
            
            if not device_sn or not plant_id:
                logger.warning(f"Device missing serial number or plant ID: {device}")
                return {}
            
            logger.debug(f"Getting data for device {device_sn}, type: {device_type}/{device_type_name}")
            
            # Wait to avoid rate limiting
            time.sleep(1)
            
            # Get device details - different methods based on device type
            device_status = None
            try:
                # Try using mix status endpoint first (for MIX/MAX/SPF type devices)
                if device_type_name and any(name in device_type_name.upper() for name in ["MIX", "SPF", "MAX"]):
                    logger.debug(f"Using get_mix_status for device {device_sn}")
                    device_status = self.growatt_api.get_mix_status(plantId=plant_id, mixSn=device_sn)
                else:
                    # For standard inverters, we need to use the plant data that includes device status
                    logger.debug(f"Using get_plant for device {device_sn}")
                    plant_data = self.growatt_api.get_plant(plantId=plant_id)
                    
                    # Find the device in the plant data
                    if plant_data and "deviceList" in plant_data:
                        for plant_device in plant_data.get("deviceList", []):
                            if plant_device.get("sn") == device_sn:
                                device_status = plant_device
                                break
            except Exception as api_e:
                logger.warning(f"Error using primary status method for device {device_sn}: {str(api_e)}")
                # If the specific method fails, try a generic approach as fallback
            
            # If we still don't have data, try using the device directly (fallback)
            if not device_status:
                logger.debug(f"Using fallback method for device {device_sn}")
                # Use device data directly from the device list
                device_status = device
            
            if not device_status:
                logger.warning(f"No data returned for device {device_sn}")
                return {}
            
            # Log the device status data for debugging
            logger.debug(f"Device status keys: {list(device_status.keys())}")
            
            # Map the raw data to our schema - adapted to handle different response formats
            inverter_data = {
                "serial_number": device_sn,
                "plant_id": plant_id,
                "model": device_type_name or device_status.get("deviceTypeName", ""),
                "firmware_version": device_status.get("firmwareVersion", ""),
                "hardware_version": device_status.get("hardwareVersion", ""),
                "nominal_power": float(device.get("nominalPower", 0)),
                # Case-insensitive field mapping to handle different response formats
                "temperature": float(device_status.get("temperature", 0)),
                # Different possible field names for the same data
                "dc_voltage_1": float(device_status.get("vPv1", device_status.get("vpv1", 0))),
                "dc_current_1": float(device_status.get("iPv1", device_status.get("ipv1", 0))),
                "dc_power_1": float(device_status.get("pPv1", device_status.get("ppv1", 0))),
                "dc_voltage_2": float(device_status.get("vPv2", device_status.get("vpv2", 0))),
                "dc_current_2": float(device_status.get("iPv2", device_status.get("ipv2", 0))),
                "dc_power_2": float(device_status.get("pPv2", device_status.get("ppv2", 0))),
                "ac_voltage": float(device_status.get("vac1", device_status.get("vac", 0))),
                "ac_current": float(device_status.get("iac", 0)),
                "ac_frequency": float(device_status.get("fAc", device_status.get("fac", 0))),
                "ac_power": float(device_status.get("pac", 0)),
                "daily_energy": float(device_status.get("eToday", 0)),
                "total_energy": float(device_status.get("eTotal", 0)),
                "operating_time": int(device_status.get("operatingTime", 0)),
                "operating_state": device_status.get("status", ""),
                "last_update_time": datetime.now(),
                "raw_data": device_status  # Store the complete raw data
            }
            
            logger.info(f"Successfully retrieved data for inverter {device_sn}")
            return inverter_data
            
        except Exception as e:
            logger.error(f"Error getting inverter data: {str(e)}")
            return {}
    
    def get_inverter_history(self, plant_id: str, device_sn: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get historical data for an inverter
        
        Args:
            plant_id: Plant ID the device belongs to
            device_sn: Device serial number
            days_back: Number of days of historical data to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of historical data points
        """
        history_data = []
        
        try:
            # Get data for each day in the range
            for day_offset in range(days_back):
                # Calculate the date
                target_date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                
                # Wait to avoid rate limiting
                time.sleep(1)
                
                # Try to get daily energy chart data based on device type
                daily_data = None
                
                try:
                    # First try using the MIX energy chart endpoint (works for MIX/MAX/SPF inverters)
                    logger.debug(f"Trying to get history data for device {device_sn} on {target_date} using MIX endpoint")
                    daily_data = self.growatt_api.get_energy_stats_daily(
                        date=target_date,
                        plantId=plant_id,
                        mixSn=device_sn
                    )
                except Exception as e:
                    logger.warning(f"Error getting MIX history data for device {device_sn}: {str(e)}")
                    daily_data = None
                
                # If that didn't work, try a different approach
                if not daily_data or not isinstance(daily_data, dict) or "obj" not in daily_data:
                    logger.debug("MIX endpoint didn't work, trying alternative methods")
                    # Could implement alternative data sources here in the future
                    # For now, just skip this device/day
                    continue
                
                # Extract chart data
                charts = daily_data.get("obj", {}).get("charts", {})
                
                if not charts:
                    logger.warning(f"No chart data found for device {device_sn} on {target_date}")
                    continue
                
                # Get timestamps from the first chart data (assuming all charts have the same timestamps)
                first_chart_key = next(iter(charts), None)
                if not first_chart_key or not charts[first_chart_key]:
                    logger.warning(f"Empty chart data for device {device_sn} on {target_date}")
                    continue
                
                # Create a dict to hold data for each timestamp
                timestamp_data = {}
                
                # Process each chart data type
                for metric, data_points in charts.items():
                    if not isinstance(data_points, list):
                        logger.warning(f"Invalid data points format for metric {metric}: {data_points}")
                        continue
                        
                    for point in data_points:
                        if not isinstance(point, list) or len(point) < 2:
                            logger.debug(f"Skipping invalid data point: {point}")
                            continue
                            
                        time_str, value = point[0], point[1]
                        
                        # Create timestamp
                        try:
                            time_parts = time_str.split(":")
                            if len(time_parts) < 2:
                                logger.debug(f"Invalid time format: {time_str}")
                                continue
                                
                            hour, minute = int(time_parts[0]), int(time_parts[1])
                            timestamp = datetime.strptime(f"{target_date} {hour:02d}:{minute:02d}:00", "%Y-%m-%d %H:%M:%S")
                            
                            # Initialize dict for this timestamp if it doesn't exist
                            if timestamp not in timestamp_data:
                                timestamp_data[timestamp] = {
                                    "serial_number": device_sn,
                                    "plant_id": plant_id,
                                    "timestamp": timestamp
                                }
                            
                            # Map different possible metric names to our database schema
                            value_float = float(value) if value is not None else 0
                            
                            # Handle various field naming conventions
                            metric_lower = metric.lower()
                            if any(m in metric_lower for m in ["ppv1", "ppv_1"]):
                                timestamp_data[timestamp]["dc_power_1"] = value_float
                            elif any(m in metric_lower for m in ["ppv2", "ppv_2"]):
                                timestamp_data[timestamp]["dc_power_2"] = value_float
                            elif metric_lower == "ppv" or "pv" in metric_lower:
                                # Total PV power
                                timestamp_data[timestamp]["dc_power_1"] = value_float
                            elif any(m in metric_lower for m in ["pac", "ac_power"]):
                                timestamp_data[timestamp]["ac_power"] = value_float
                            elif "temperature" in metric_lower or "temp" in metric_lower:
                                timestamp_data[timestamp]["temperature"] = value_float
                            elif "energy" in metric_lower or "e_" in metric_lower:
                                timestamp_data[timestamp]["energy"] = value_float
                            
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Error processing data point {point}: {str(e)}")
                
                # Add all timestamp data to the history data list
                for timestamp, data in timestamp_data.items():
                    # Only add points that have at least one power value
                    if data.get("dc_power_1") or data.get("dc_power_2") or data.get("ac_power"):
                        history_data.append(data)
                
                points_count = len([d for d in timestamp_data.values() if d.get("dc_power_1") or d.get("dc_power_2") or d.get("ac_power")])
                if points_count > 0:
                    logger.info(f"Successfully retrieved {points_count} history points for device {device_sn} on {target_date}")
                else:
                    logger.warning(f"No valid power data points found for device {device_sn} on {target_date}")
            
            return history_data
            
        except Exception as e:
            logger.error(f"Error getting inverter history: {str(e)}")
            return []
    
    def save_inverter_data_to_db(self, inverter_data: Dict[str, Any]) -> bool:
        """
        Save inverter data to the database
        
        Args:
            inverter_data: Inverter data dictionary
            
        Returns:
            bool: True if data was saved successfully, False otherwise
        """
        if not inverter_data or "serial_number" not in inverter_data:
            logger.warning("Invalid inverter data, missing required fields")
            return False
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Convert raw_data to JSON string
                raw_data = json.dumps(inverter_data.get("raw_data", {}))
                
                # Insert/update inverter details
                cursor.execute("""
                    INSERT INTO inverter_details (
                        serial_number, plant_id, model, firmware_version, hardware_version,
                        nominal_power, max_ac_power, max_dc_power, efficiency, temperature,
                        dc_voltage_1, dc_current_1, dc_power_1, dc_voltage_2, dc_current_2, dc_power_2,
                        ac_voltage, ac_current, ac_frequency, ac_power, daily_energy, total_energy,
                        operating_time, operating_state, last_update_time, raw_data
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (serial_number, collected_at)
                    DO UPDATE SET
                        plant_id = EXCLUDED.plant_id,
                        model = EXCLUDED.model,
                        firmware_version = EXCLUDED.firmware_version,
                        hardware_version = EXCLUDED.hardware_version,
                        nominal_power = EXCLUDED.nominal_power,
                        max_ac_power = EXCLUDED.max_ac_power,
                        max_dc_power = EXCLUDED.max_dc_power,
                        efficiency = EXCLUDED.efficiency,
                        temperature = EXCLUDED.temperature,
                        dc_voltage_1 = EXCLUDED.dc_voltage_1,
                        dc_current_1 = EXCLUDED.dc_current_1,
                        dc_power_1 = EXCLUDED.dc_power_1,
                        dc_voltage_2 = EXCLUDED.dc_voltage_2,
                        dc_current_2 = EXCLUDED.dc_current_2,
                        dc_power_2 = EXCLUDED.dc_power_2,
                        ac_voltage = EXCLUDED.ac_voltage,
                        ac_current = EXCLUDED.ac_current,
                        ac_frequency = EXCLUDED.ac_frequency,
                        ac_power = EXCLUDED.ac_power,
                        daily_energy = EXCLUDED.daily_energy,
                        total_energy = EXCLUDED.total_energy,
                        operating_time = EXCLUDED.operating_time,
                        operating_state = EXCLUDED.operating_state,
                        last_update_time = EXCLUDED.last_update_time,
                        raw_data = EXCLUDED.raw_data
                """, (
                    inverter_data["serial_number"],
                    inverter_data["plant_id"],
                    inverter_data.get("model", ""),
                    inverter_data.get("firmware_version", ""),
                    inverter_data.get("hardware_version", ""),
                    inverter_data.get("nominal_power", 0),
                    inverter_data.get("max_ac_power", 0),
                    inverter_data.get("max_dc_power", 0),
                    inverter_data.get("efficiency", 0),
                    inverter_data.get("temperature", 0),
                    inverter_data.get("dc_voltage_1", 0),
                    inverter_data.get("dc_current_1", 0),
                    inverter_data.get("dc_power_1", 0),
                    inverter_data.get("dc_voltage_2", 0),
                    inverter_data.get("dc_current_2", 0),
                    inverter_data.get("dc_power_2", 0),
                    inverter_data.get("ac_voltage", 0),
                    inverter_data.get("ac_current", 0),
                    inverter_data.get("ac_frequency", 0),
                    inverter_data.get("ac_power", 0),
                    inverter_data.get("daily_energy", 0),
                    inverter_data.get("total_energy", 0),
                    inverter_data.get("operating_time", 0),
                    inverter_data.get("operating_state", ""),
                    inverter_data.get("last_update_time", datetime.now()),
                    raw_data
                ))
                
                conn.commit()
                logger.info(f"Successfully saved data for inverter {inverter_data['serial_number']}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving inverter data to database: {str(e)}")
            return False
    
    def save_inverter_history_to_db(self, history_data: List[Dict[str, Any]]) -> int:
        """
        Save inverter history data to the database
        
        Args:
            history_data: List of inverter history data points
            
        Returns:
            int: Number of data points saved successfully
        """
        if not history_data:
            logger.warning("No history data to save")
            return 0
        
        saved_count = 0
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                for data_point in history_data:
                    # Check required fields
                    if not all(k in data_point for k in ["serial_number", "plant_id", "timestamp"]):
                        logger.warning(f"History data point missing required fields: {data_point}")
                        continue
                    
                    # Insert/update history data
                    cursor.execute("""
                        INSERT INTO inverter_history (
                            serial_number, plant_id, timestamp, dc_voltage_1, dc_current_1, dc_power_1,
                            dc_voltage_2, dc_current_2, dc_power_2, ac_voltage, ac_current, ac_frequency,
                            ac_power, temperature, energy
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (serial_number, timestamp)
                        DO UPDATE SET
                            plant_id = EXCLUDED.plant_id,
                            dc_voltage_1 = EXCLUDED.dc_voltage_1,
                            dc_current_1 = EXCLUDED.dc_current_1,
                            dc_power_1 = EXCLUDED.dc_power_1,
                            dc_voltage_2 = EXCLUDED.dc_voltage_2,
                            dc_current_2 = EXCLUDED.dc_current_2,
                            dc_power_2 = EXCLUDED.dc_power_2,
                            ac_voltage = EXCLUDED.ac_voltage,
                            ac_current = EXCLUDED.ac_current,
                            ac_frequency = EXCLUDED.ac_frequency,
                            ac_power = EXCLUDED.ac_power,
                            temperature = EXCLUDED.temperature,
                            energy = EXCLUDED.energy,
                            collected_at = CURRENT_TIMESTAMP
                    """, (
                        data_point["serial_number"],
                        data_point["plant_id"],
                        data_point["timestamp"],
                        data_point.get("dc_voltage_1", 0),
                        data_point.get("dc_current_1", 0),
                        data_point.get("dc_power_1", 0),
                        data_point.get("dc_voltage_2", 0),
                        data_point.get("dc_current_2", 0),
                        data_point.get("dc_power_2", 0),
                        data_point.get("ac_voltage", 0),
                        data_point.get("ac_current", 0),
                        data_point.get("ac_frequency", 0),
                        data_point.get("ac_power", 0),
                        data_point.get("temperature", 0),
                        data_point.get("energy", 0)
                    ))
                    
                    saved_count += 1
                
                conn.commit()
                logger.info(f"Successfully saved {saved_count} history data points")
                return saved_count
                
        except Exception as e:
            logger.error(f"Error saving inverter history to database: {str(e)}")
            return saved_count
    
    def run(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Run the data collection process
        
        Args:
            days_back: Number of days of historical data to collect
            
        Returns:
            Dict[str, Any]: Collection results
        """
        result = {
            "success": False,
            "message": "",
            "inverters_processed": 0,
            "inverters_success": 0,
            "history_points_processed": 0,
            "history_points_success": 0
        }
        
        try:
            # Authenticate with the API
            if not self.is_authenticated and not self.authenticate():
                result["message"] = "Failed to authenticate with the Growatt API"
                return result
            
            # Ensure database tables exist
            if not ensure_database_tables():
                result["message"] = "Failed to ensure database tables"
                return result
            
            # Get all plants
            plants = self.get_plants()
            
            if not plants:
                result["message"] = "No plants found"
                return result
            
            # Process each plant
            for plant in plants:
                plant_id = plant.get("id", "")
                plant_name = plant.get("plantName", "Unknown Plant")
                if not plant_id:
                    logger.warning(f"Plant missing ID: {plant}")
                    continue
                
                logger.info(f"Processing plant: {plant_name} (ID: {plant_id})")
                
                # Get devices for the plant
                devices = self.get_devices_for_plant(plant_id)
                if not devices:
                    logger.warning(f"No devices found for plant {plant_id}")
                    continue
                    
                logger.info(f"Found {len(devices)} devices for plant {plant_id}")
                
                # Process each device
                for device in devices:
                    # Get device info
                    device_sn = device.get("deviceSn", "")
                    device_type = device.get("deviceType", "")
                    device_type_name = device.get("deviceTypeName", "")
                    device_alias = device.get("deviceAilas", device.get("alias", "Unknown Device"))
                    
                    if not device_sn:
                        logger.warning(f"Device missing serial number in plant {plant_id}")
                        continue
                    
                    # Log device details
                    logger.info(f"Processing device: {device_alias} (SN: {device_sn}, Type: {device_type_name})")
                    
                    # Increment counter
                    result["inverters_processed"] += 1
                    
                    # Get inverter data
                    inverter_data = self.get_inverter_data(device)
                    
                    if inverter_data:
                        logger.info(f"Retrieved data for device {device_sn}")
                        # Save inverter data to database
                        if self.save_inverter_data_to_db(inverter_data):
                            result["inverters_success"] += 1
                            logger.info(f"Successfully saved data for device {device_sn}")
                        else:
                            logger.warning(f"Failed to save data for device {device_sn}")
                    else:
                        logger.warning(f"No data retrieved for device {device_sn}")
                    
                    # Get inverter history data
                    try:
                        logger.info(f"Getting history data for device {device_sn}")
                        history_data = self.get_inverter_history(plant_id, device_sn, days_back)
                        
                        if history_data:
                            # Count history points
                            result["history_points_processed"] += len(history_data)
                            logger.info(f"Retrieved {len(history_data)} history points for device {device_sn}")
                            
                            # Save history data to database
                            saved_count = self.save_inverter_history_to_db(history_data)
                            result["history_points_success"] += saved_count
                            logger.info(f"Successfully saved {saved_count} history points for device {device_sn}")
                        else:
                            logger.warning(f"No history data retrieved for device {device_sn}")
                    except Exception as e:
                        logger.error(f"Error processing history data for device {device_sn}: {str(e)}")
            
            # Set success flag
            result["success"] = True
            result["message"] = "Data collection completed successfully"
            
            return result
            
        except Exception as e:
            logger.error(f"Error during data collection: {str(e)}")
            result["message"] = f"Error during data collection: {str(e)}"
            return result

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Collect inverter data from Growatt API")
    parser.add_argument("--server", dest="server_url", default="http://localhost:8000", 
                      help="URL of the server running the Growatt monitor")
    parser.add_argument("--days", dest="days_back", type=int, default=7,
                      help="Number of days of historical data to collect")
    parser.add_argument("--verbose", dest="verbose", action="store_true", 
                      help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Ensure logs directory exists
    ensure_logs_dir()
    
    logger.info(f"Starting inverter data collection from {args.server_url}")
    
    # Initialize collector
    collector = InverterDataCollector(server_url=args.server_url)
    
    # Run collection
    result = collector.run(days_back=args.days_back)
    
    if result["success"]:
        logger.info(f"Inverter data collection completed successfully: {result}")
        print(f"SUCCESS: Processed {result['inverters_processed']} inverters, saved {result['inverters_success']} inverters and {result['history_points_success']} history points")
        return 0
    else:
        logger.error(f"Inverter data collection failed: {result}")
        print(f"ERROR: {result['message']}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 