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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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
    Fetch energy production data for the specified timeframe from the database
    
    Args:
        timeframe: Either 'daily', 'weekly', or 'monthly'
        
    Returns:
        Dict containing energy data for all devices
    """
    try:
        from app.database import DatabaseConnector
        from app.config import Config
        
        # Initialize database connector
        db = DatabaseConnector()
        
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
        
        # Format dates for database query
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        logger.info(f"Fetching {timeframe} energy data from {start_date_str} to {end_date_str}")
        
        # Query plants from database
        plants_query = """
            SELECT id, name
            FROM plants
            ORDER BY name
        """
        plants = db.query(plants_query)
        
        all_data = {
            'timeframe': timeframe,
            'start_date': start_date,
            'end_date': end_date,
            'date_format': date_format,
            'plants': []
        }
        
        # Fetch energy data for each plant
        for plant in plants:
            plant_id = plant['id']
            plant_name = plant['name']
            
            plant_data = {
                'plant_id': plant_id,
                'plant_name': plant_name,
                'devices': []
            }
            
            # Fetch devices for this plant
            devices_query = """
                SELECT serial_number, alias, type
                FROM devices
                WHERE plant_id = %s
                ORDER BY alias
            """
            devices = db.query(devices_query, (plant_id,))
            
            # For each device, fetch energy data
            for device in devices:
                serial_number = device['serial_number']
                device_alias = device['alias'] or serial_number
                
                device_data = {
                    'serial_number': serial_number,
                    'alias': device_alias,
                    'energy_data': []
                }
                
                # Fetch energy stats from the energy_stats table
                energy_query = """
                    SELECT date, daily_energy as energy
                    FROM energy_stats
                    WHERE mix_sn = %s AND date BETWEEN %s AND %s
                    ORDER BY date
                """
                energy_results = db.query(energy_query, (serial_number, start_date_str, end_date_str))
                
                # Format the results for the chart generator
                for data in energy_results:
                    device_data['energy_data'].append({
                        'date': data['date'],
                        'energy': float(data['energy'] or 0)
                    })
                
                # Add device data to plant if we have energy data
                if device_data['energy_data']:
                    plant_data['devices'].append(device_data)
            
            # Add plant to all_data if it has devices with data
            if plant_data['devices']:
                all_data['plants'].append(plant_data)
        
        return all_data
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching energy data: {e}")
        logger.exception(e)  # Log the full traceback
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
        # Check if we have data to generate charts
        has_data = bool(energy_data and energy_data.get('plants'))
        
        timeframe = energy_data.get('timeframe', 'daily')
        date_format = energy_data.get('date_format', '%Y-%m-%d')
        chart_paths = []
        
        # Set up styling for charts
        plt.style.use('ggplot')
        
        # Create a no-data chart if we don't have any energy data
        if not has_data:
            logger.warning("No energy data available, generating a no-data chart")
            no_data_chart = generate_no_data_chart(timeframe)
            if no_data_chart:
                chart_paths.append(no_data_chart)
            return chart_paths
            
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

def generate_no_data_chart(timeframe: str) -> Optional[str]:
    """
    Generate a chart indicating no data is available
    
    Args:
        timeframe: The timeframe that was requested
        
    Returns:
        Path to the generated chart file
    """
    try:
        # Create a figure
        plt.figure(figsize=(10, 6))
        
        # Add a text message
        if timeframe == 'daily':
            title = "Daily Energy Production - Last 24 Hours"
            message = "No energy data available for the past 24 hours"
        elif timeframe == 'weekly':
            title = "Weekly Energy Production - Last 7 Days"
            message = "No energy data available for the past 7 days"
        elif timeframe == 'monthly':
            title = "Monthly Energy Production - Last 30 Days"
            message = "No energy data available for the past 30 days"
        else:
            title = "Energy Production Report"
            message = "No energy data available for the requested period"
        
        # Set title
        plt.title(title, fontsize=16)
        
        # Turn off axis
        plt.axis('off')
        
        # Add message in the center
        plt.text(0.5, 0.5, message, 
                ha='center', va='center', 
                fontsize=14, 
                transform=plt.gca().transAxes,
                bbox=dict(boxstyle='round,pad=1', facecolor='#f8f9fa', alpha=0.8))
        
        # Add current date and time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plt.text(0.5, 0.3, f"Report generated at: {current_time}", 
                ha='center', va='center', 
                fontsize=10, 
                transform=plt.gca().transAxes)
        
        # Save chart
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name, bbox_inches='tight', dpi=300)
        plt.close()
        
        logger.info(f"Generated no-data chart: {temp_file.name}")
        return temp_file.name
    
    except Exception as e:
        logger.error(f"Error generating no-data chart: {e}")
        return None

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
    parser.add_argument("--telegram", action="store_true", help="Send report via Telegram")
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
        
        # Generate charts (will create a no-data chart if no data available)
        chart_paths = generate_charts(energy_data)
        if not chart_paths:
            logger.error("Failed to generate any charts")
            return 1
            
        # Send reports via Telegram if requested
        if args.telegram:
            success = send_telegram_reports(chart_paths, timeframe)
            
            if success:
                logger.info(f"Successfully sent {timeframe} energy report via Telegram")
            else:
                logger.error(f"Failed to send {timeframe} energy report via Telegram")
                return 1
        else:
            logger.info(f"Generated {len(chart_paths)} charts for {timeframe} energy report")
            for path in chart_paths:
                logger.info(f"Chart saved at: {path}")
                
        return 0
            
    except Exception as e:
        logger.error(f"Error in energy report script: {e}")
        return 1

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    sys.exit(main())
