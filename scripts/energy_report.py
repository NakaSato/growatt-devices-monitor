#!/usr/bin/env python3
"""
Generate and send energy production reports via Telegram

This script generates visual reports of energy production data 
and sends them via Telegram as charts.

Usage:
    python energy_report.py [--daily|--weekly|--monthly] [--debug]
"""

import os
import sys
import logging
import argparse
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# Set up path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/energy_reports.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def fetch_energy_data(timeframe: str) -> Dict[str, Any]:
    """
    Fetch energy production data for the specified timeframe
    
    Args:
        timeframe: Either 'daily', 'weekly', or 'monthly'
        
    Returns:
        Dict containing energy data for all devices
    """
    try:
        from app.core.growatt import Growatt
        from app.config import Config
        from datetime import datetime, timedelta
        
        # Initialize Growatt API
        growatt_api = Growatt()
        
        # Authenticate
        login_result = growatt_api.login(
            username=Config.GROWATT_USERNAME,
            password=Config.GROWATT_PASSWORD
        )
        if not login_result:
            logger.error("Failed to login to Growatt API")
            return {}
        
        # Calculate date range based on timeframe
        end_date = datetime.now()
        
        if timeframe == 'daily':
            # Last 24 hours
            start_date = end_date - timedelta(days=1)
            date_format = "%Y-%m-%d %H:%M"
        elif timeframe == 'weekly':
            # Last 7 days
            start_date = end_date - timedelta(days=7)
            date_format = "%Y-%m-%d"
        elif timeframe == 'monthly':
            # Last 30 days
            start_date = end_date - timedelta(days=30)
            date_format = "%Y-%m-%d"
        else:
            logger.error(f"Invalid timeframe: {timeframe}")
            return {}
        
        # Format dates for API
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        logger.info(f"Fetching {timeframe} energy data from {start_date_str} to {end_date_str}")
        
        # Fetch plants
        plants = growatt_api.get_plants()
        if not plants:
            logger.error("Failed to fetch plants")
            return {}
            
        all_data = {
            'timeframe': timeframe,
            'start_date': start_date,
            'end_date': end_date,
            'date_format': date_format,
            'plants': []
        }
        
        # Fetch energy data for each plant
        for plant in plants:
            plant_id = plant.get('id')
            plant_name = plant.get('plantName', 'Unknown Plant')
            
            plant_data = {
                'plant_id': plant_id,
                'plant_name': plant_name,
                'devices': []
            }
            
            # Fetch devices for this plant
            devices_result = growatt_api.get_device_list(plant_id)
            if not devices_result or 'obj' not in devices_result or 'datas' not in devices_result['obj']:
                logger.warning(f"Failed to fetch devices for plant {plant_id}")
                continue
                
            devices = devices_result['obj']['datas']
            
            # For each device, fetch energy data
            for device in devices:
                serial_number = device.get('sn') or device.get('deviceSn')
                device_alias = device.get('alias') or device.get('deviceAilas') or device.get('deviceName', 'Unknown Device')
                
                device_data = {
                    'serial_number': serial_number,
                    'alias': device_alias,
                    'energy_data': []
                }
                
                # Fetch the appropriate energy data based on timeframe
                try:
                    if timeframe == 'daily':
                        # For daily, get hourly data for the past 24 hours
                        energy_result = growatt_api.get_energy_stats_daily(
                            start_date_str, plant_id, serial_number
                        )
                    elif timeframe == 'weekly':
                        # For weekly, get daily data for the past 7 days
                        energy_result = {}
                        for d in range(7):
                            current_date = start_date + timedelta(days=d)
                            current_date_str = current_date.strftime("%Y-%m-%d")
                            daily_data = growatt_api.get_energy_stats_daily(
                                current_date_str, plant_id, serial_number
                            )
                            if daily_data and 'obj' in daily_data and 'etoday' in daily_data['obj']:
                                energy_data = {
                                    'date': current_date_str,
                                    'energy': daily_data['obj']['etoday']
                                }
                                device_data['energy_data'].append(energy_data)
                    elif timeframe == 'monthly':
                        # For monthly, get daily data for the past 30 days
                        energy_result = {}
                        for d in range(30):
                            current_date = start_date + timedelta(days=d)
                            current_date_str = current_date.strftime("%Y-%m-%d")
                            daily_data = growatt_api.get_energy_stats_daily(
                                current_date_str, plant_id, serial_number
                            )
                            if daily_data and 'obj' in daily_data and 'etoday' in daily_data['obj']:
                                energy_data = {
                                    'date': current_date_str,
                                    'energy': daily_data['obj']['etoday']
                                }
                                device_data['energy_data'].append(energy_data)
                    
                    # Daily data needs special handling to extract hourly values
                    if timeframe == 'daily' and energy_result and 'obj' in energy_result and 'charts' in energy_result['obj']:
                        hourly_data = energy_result['obj']['charts'].get('pac', [])
                        hours = len(hourly_data)
                        for i, value in enumerate(hourly_data):
                            if value is not None and value > 0:
                                # Create hour timestamp
                                hour = i % 24
                                hour_str = f"{start_date_str} {hour:02d}:00"
                                energy_data = {
                                    'date': hour_str,
                                    'energy': value
                                }
                                device_data['energy_data'].append(energy_data)
                except Exception as e:
                    logger.warning(f"Failed to fetch energy data for device {serial_number}: {e}")
                
                plant_data['devices'].append(device_data)
            
            all_data['plants'].append(plant_data)
        
        return all_data
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching energy data: {e}")
        return {}

def generate_charts(energy_data: Dict[str, Any]) -> List[str]:
    """
    Generate charts from energy data
    
    Args:
        energy_data: Dictionary containing energy data
        
    Returns:
        List of paths to generated chart files
    """
    try:
        if not energy_data or not energy_data.get('plants'):
            logger.error("No energy data to generate charts")
            return []
        
        timeframe = energy_data.get('timeframe', 'daily')
        date_format = energy_data.get('date_format', '%Y-%m-%d')
        chart_paths = []
        
        # Set up styling for charts
        plt.style.use('ggplot')
        
        # Generate a summary chart for all plants combined
        summary_chart_path = generate_summary_chart(energy_data)
        if summary_chart_path:
            chart_paths.append(summary_chart_path)
        
        # Generate individual charts for each plant
        for plant in energy_data.get('plants', []):
            plant_chart_path = generate_plant_chart(plant, timeframe, date_format)
            if plant_chart_path:
                chart_paths.append(plant_chart_path)
        
        return chart_paths
        
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
        return []

def generate_summary_chart(energy_data: Dict[str, Any]) -> Optional[str]:
    """
    Generate a summary chart for all plants
    
    Args:
        energy_data: Dictionary containing energy data
        
    Returns:
        Path to generated chart file or None if error
    """
    try:
        timeframe = energy_data.get('timeframe', 'daily')
        date_format = energy_data.get('date_format', '%Y-%m-%d')
        
        # Create a DataFrame to aggregate all plant data
        all_data = []
        
        for plant in energy_data.get('plants', []):
            plant_name = plant.get('plant_name', 'Unknown Plant')
            
            for device in plant.get('devices', []):
                for entry in device.get('energy_data', []):
                    date_value = entry.get('date', '').strip()
                    energy_value = float(entry.get('energy', 0))
                    
                    if date_value and energy_value >= 0:
                        all_data.append({
                            'plant': plant_name,
                            'date': date_value,
                            'energy': energy_value
                        })
        
        if not all_data:
            logger.warning("No valid data for summary chart")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        # Group by date and sum energy values
        summary_df = df.groupby('date')['energy'].sum().reset_index()
        
        # Sort by date
        summary_df['date'] = pd.to_datetime(summary_df['date'])
        summary_df = summary_df.sort_values('date')
        
        # Create figure
        plt.figure(figsize=(12, 7))
        
        # Plot the data
        plt.bar(summary_df['date'], summary_df['energy'], color='#2ecc71', width=0.6)
        
        # Format x-axis dates based on timeframe
        if timeframe == 'daily':
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=2))
            title = f"Hourly Energy Production - {energy_data.get('start_date', '').strftime('%Y-%m-%d')}"
        elif timeframe == 'weekly':
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator())
            title = "Daily Energy Production - Last 7 Days"
        elif timeframe == 'monthly':
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
            title = "Daily Energy Production - Last 30 Days"
        
        # Add title and labels
        plt.title(title, fontsize=16)
        plt.ylabel('Energy (kWh)', fontsize=12)
        plt.xlabel('Date', fontsize=12)
        
        # Add grid
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Rotate date labels for better readability
        plt.xticks(rotation=45)
        
        # Tight layout
        plt.tight_layout()
        
        # Save chart to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, bbox_inches='tight', dpi=300)
        plt.close()
        
        logger.info(f"Generated summary chart: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Error generating summary chart: {e}")
        return None

def generate_plant_chart(plant_data: Dict[str, Any], timeframe: str, date_format: str) -> Optional[str]:
    """
    Generate a chart for a specific plant
    
    Args:
        plant_data: Dictionary containing plant data
        timeframe: Either 'daily', 'weekly', or 'monthly'
        date_format: Date format for parsing
        
    Returns:
        Path to generated chart file or None if error
    """
    try:
        plant_name = plant_data.get('plant_name', 'Unknown Plant')
        devices = plant_data.get('devices', [])
        
        if not devices:
            logger.warning(f"No devices found for plant {plant_name}")
            return None
            
        # Create figure with subplots for each device
        num_devices = len(devices)
        if num_devices > 3:
            # For many devices, use a grid layout
            rows = int(np.ceil(num_devices / 2))
            cols = min(num_devices, 2)
            fig, axes = plt.subplots(rows, cols, figsize=(12, 5*rows))
            axes = axes.flatten() if num_devices > 1 else [axes]
        else:
            # For few devices, stack vertically
            fig, axes = plt.subplots(num_devices, 1, figsize=(12, 5*num_devices))
            axes = [axes] if num_devices == 1 else axes
        
        for i, device in enumerate(devices):
            device_name = device.get('alias', f"Device {i+1}")
            energy_data = device.get('energy_data', [])
            
            # Skip if no data
            if not energy_data:
                axes[i].text(0.5, 0.5, f"No data available for {device_name}", 
                             horizontalalignment='center', verticalalignment='center',
                             transform=axes[i].transAxes)
                continue
            
            # Convert to DataFrame
            data = []
            for entry in energy_data:
                date_value = entry.get('date', '').strip()
                energy_value = float(entry.get('energy', 0))
                
                if date_value and energy_value >= 0:
                    data.append({
                        'date': date_value,
                        'energy': energy_value
                    })
            
            if not data:
                axes[i].text(0.5, 0.5, f"No valid data for {device_name}", 
                             horizontalalignment='center', verticalalignment='center',
                             transform=axes[i].transAxes)
                continue
                
            # Create DataFrame and sort by date
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Plot data
            axes[i].bar(df['date'], df['energy'], color='#3498db', width=0.6)
            
            # Set title and labels
            axes[i].set_title(f"{device_name}", fontsize=12)
            axes[i].set_ylabel('Energy (kWh)', fontsize=10)
            
            # Format x-axis based on timeframe
            if timeframe == 'daily':
                axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                axes[i].xaxis.set_major_locator(mdates.HourLocator(interval=2))
            elif timeframe == 'weekly':
                axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%a %d'))
                axes[i].xaxis.set_major_locator(mdates.DayLocator())
            elif timeframe == 'monthly':
                axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
                axes[i].xaxis.set_major_locator(mdates.DayLocator(interval=5))
            
            # Rotate x-axis labels
            plt.setp(axes[i].xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Add grid
            axes[i].grid(True, linestyle='--', alpha=0.7)
            
            # Add total energy as text
            total_energy = df['energy'].sum()
            axes[i].text(0.02, 0.95, f"Total: {total_energy:.2f} kWh", 
                        transform=axes[i].transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', alpha=0.1))
        
        # Clean up unused subplots
        for j in range(i+1, len(axes)):
            axes[j].axis('off')
        
        # Add main title
        if timeframe == 'daily':
            title = f"{plant_name} - Hourly Energy Production"
        elif timeframe == 'weekly':
            title = f"{plant_name} - Daily Energy Production (Last 7 Days)"
        elif timeframe == 'monthly':
            title = f"{plant_name} - Daily Energy Production (Last 30 Days)"
        
        plt.suptitle(title, fontsize=16)
        
        # Tight layout
        plt.tight_layout(rect=[0, 0, 1, 0.97])  # Make room for the main title
        
        # Save chart to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, bbox_inches='tight', dpi=300)
        plt.close()
        
        logger.info(f"Generated plant chart for {plant_name}: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Error generating plant chart for {plant_data.get('plant_name', 'Unknown')}: {e}")
        return None

def send_telegram_reports(chart_paths: List[str], timeframe: str) -> bool:
    """
    Send charts via Telegram
    
    Args:
        chart_paths: List of paths to chart files
        timeframe: Report timeframe (daily, weekly, monthly)
        
    Returns:
        bool: True if at least one chart was sent successfully
    """
    try:
        from app.services.notification_service import NotificationService
        
        # Initialize notification service
        notification_service = NotificationService()
        
        # Check if Telegram is enabled
        if not notification_service.telegram_enabled:
            logger.error("Telegram notifications are not enabled")
            return False
            
        # Send title message
        if timeframe == 'daily':
            title = "📊 Daily Energy Production Report"
            description = f"Energy production for {datetime.now().strftime('%Y-%m-%d')}"
        elif timeframe == 'weekly':
            title = "📊 Weekly Energy Production Report"
            description = f"Energy production for the past 7 days"
        elif timeframe == 'monthly':
            title = "📊 Monthly Energy Production Report"
            description = f"Energy production for the past 30 days"
        else:
            title = "📊 Energy Production Report"
            description = "Energy production summary"
            
        # Send the title message
        notification_service._send_telegram(
            f"<b>{title}</b>\n\n{description}\n\nGenerating charts..."
        )
        
        # Send each chart
        success = False
        for i, chart_path in enumerate(chart_paths):
            # Generate caption
            if i == 0:
                caption = f"<b>{title}</b>\n\nTotal energy production across all plants"
            else:
                caption = f"<b>Plant Details ({i}/{len(chart_paths)-1})</b>"
                
            # Send the chart
            result = notification_service.send_telegram_photo(chart_path, caption)
            success |= result
            
            # Clean up the file
            try:
                os.unlink(chart_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {chart_path}: {e}")
        
        # Send closing message
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        notification_service._send_telegram(
            f"<b>Report generated at:</b> {now}\n\n"
            f"<i>For more details, check the web dashboard.</i>"
        )
        
        return success
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Telegram reports: {e}")
        return False

def main():
    """
    Main function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate and send energy production reports via Telegram")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--daily", action="store_true", help="Generate daily report (last 24 hours)")
    group.add_argument("--weekly", action="store_true", help="Generate weekly report (last 7 days)")
    group.add_argument("--monthly", action="store_true", help="Generate monthly report (last 30 days)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
    
    try:
        # Determine timeframe
        timeframe = 'daily' if args.daily else 'weekly' if args.weekly else 'monthly'
        
        logger.info(f"Starting {timeframe} energy report generation")
        
        # Fetch energy data
        energy_data = fetch_energy_data(timeframe)
        if not energy_data:
            logger.error("Failed to fetch energy data")
            return 1
            
        # Generate charts
        chart_paths = generate_charts(energy_data)
        if not chart_paths:
            logger.error("Failed to generate charts")
            return 1
            
        # Send reports via Telegram
        success = send_telegram_reports(chart_paths, timeframe)
        
        if success:
            logger.info(f"Successfully sent {timeframe} energy report via Telegram")
            return 0
        else:
            logger.error(f"Failed to send {timeframe} energy report via Telegram")
            return 1
            
    except Exception as e:
        logger.error(f"Error in energy report script: {e}")
        return 1

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    sys.exit(main())
