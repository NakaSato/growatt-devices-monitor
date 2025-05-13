#!/usr/bin/env python3
"""
Script for generating inverter reports with data visualization and sending them via email and Telegram.

This script queries the database for inverter details, generates visualizations,
creates a PDF report, and sends it via email and/or Telegram.

Usage:
    python inverter_report.py [--days DAYS] [--debug] [--email EMAIL] [--telegram]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from pathlib import Path
import requests
import json

# Configure logging to write to file
LOG_FILE = "logs/inverter_report.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set path to include the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up fonts for Thai text
# First check for our own bundled font
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
bundled_font_path = os.path.join(project_root, 'fonts', 'thai', 'Sarabun-Regular.ttf')

# List of potential Thai font paths on different operating systems
font_paths = [
    # Our own bundled font (first priority)
    bundled_font_path,
    # Thai fonts usually found on macOS systems
    '/Library/Fonts/Arial Unicode.ttf',
    '/Library/Fonts/Thonburi.ttc',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    '/System/Library/Fonts/Thonburi.ttc',
    # Thai fonts on Linux systems
    '/usr/share/fonts/truetype/thai/Garuda.ttf',
    '/usr/share/fonts/truetype/thai/Norasi.ttf',
    '/usr/share/fonts/truetype/thai/TlwgTypo.ttf',
    '/usr/share/fonts/truetype/thai/TlwgMono.ttf',
    '/usr/share/fonts/truetype/thai/Sarabun.ttf',
    '/usr/share/fonts/truetype/thai-tlwg/Garuda.ttf',
    '/usr/share/fonts/truetype/thai-tlwg/Norasi.ttf',
    '/usr/share/fonts/truetype/thai-tlwg/TlwgTypo.ttf',
    '/usr/share/fonts/truetype/thai-tlwg/TlwgMono.ttf',
    '/usr/share/fonts/truetype/thai-tlwg/Sarabun.ttf',
    # Common fonts that may have Thai support
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    # Windows fonts
    'C:/Windows/Fonts/arial.ttf',
    'C:/Windows/Fonts/arialuni.ttf',
    'C:/Windows/Fonts/tahoma.ttf',
]

# Try to register all available Thai fonts with matplotlib
registered_fonts = []
for font_path in font_paths:
    if os.path.exists(font_path):
        try:
            logger.info(f"Found Thai font: {font_path}")
            font_prop = fm.FontProperties(fname=font_path)
            registered_fonts.append(font_prop)
            
            # Register the font with matplotlib
            font_name = fm.FontProperties(fname=font_path).get_name()
            matplotlib.font_manager.fontManager.addfont(font_path)
            
            # If this is the first font, set it as default
            if not plt.rcParams.get('font.family', None):
                plt.rcParams['font.family'] = font_name
                logger.info(f"Using {font_name} as primary font")
        except Exception as e:
            logger.warning(f"Failed to load font {font_path}: {e}")

# Set fontconfig patterns as fallback
if not registered_fonts:
    logger.warning("No suitable Thai font found. Using fallback fonts.")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = [
        'TH Sarabun New', 'Thonburi', 'Garuda', 'Norasi', 
        'TlwgTypo', 'TlwgMono', 'Arial Unicode MS', 'Tahoma', 
        'DejaVu Sans', 'Arial'
    ]
else:
    logger.info(f"Successfully registered {len(registered_fonts)} Thai fonts")

# Configure matplotlib to use Thai font for all text
matplotlib.rcParams['axes.unicode_minus'] = False  # Fix for minus sign

def fetch_inverter_data(days: int = 7) -> pd.DataFrame:
    """
    Fetch inverter data from the database for the specified number of days
    
    Args:
        days: Number of days to look back
        
    Returns:
        pd.DataFrame: DataFrame containing inverter details
    """
    try:
        from app.database import DatabaseConnector
        
        # Initialize database connector
        db = DatabaseConnector()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for SQL
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # First, let's query the database to get the column names of the inverter_details table
        # This will help us identify the correct column names
        try:
            columns_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'inverter_details'
            """
            columns = db.query(columns_query)
            column_names = [col[0] for col in columns] if columns else []
            logger.debug(f"Inverter_details table columns: {column_names}")
            
            if not column_names:
                logger.error("No columns found in inverter_details table or table doesn't exist")
                return pd.DataFrame()
            
            # Look for column that might contain the serial number
            serial_column = None
            possible_names = ['serial_number', 'inverter_serial', 'device_serial', 'serial']
            for name in possible_names:
                if name in column_names:
                    serial_column = name
                    break
            
            if not serial_column:
                logger.error("Could not identify serial number column in inverter_details table")
                return pd.DataFrame()
            
            # Look for timestamp column - it might have different names
            timestamp_column = None
            possible_timestamp_names = ['timestamp', 'created_at', 'recorded_at', 'date_time', 'time']
            for name in possible_timestamp_names:
                if name in column_names:
                    timestamp_column = name
                    break
            
            if not timestamp_column:
                logger.error("Could not identify timestamp column in inverter_details table")
                return pd.DataFrame()
            
            logger.info(f"Using '{serial_column}' as the serial number column and '{timestamp_column}' as the timestamp column")
            
            # Build a dynamic list of columns to select
            # Define essential columns and their possible alternates
            column_mapping = {
                'pv1_voltage': ['pv1_voltage', 'pv1voltage', 'pv1_v'],
                'pv1_current': ['pv1_current', 'pv1current', 'pv1_c', 'pv1_i'],
                'pv1_power': ['pv1_power', 'pv1power', 'pv1_p', 'pv1_w'],
                'pv2_voltage': ['pv2_voltage', 'pv2voltage', 'pv2_v'],
                'pv2_current': ['pv2_current', 'pv2current', 'pv2_c', 'pv2_i'],
                'pv2_power': ['pv2_power', 'pv2power', 'pv2_p', 'pv2_w'],
                'pv3_voltage': ['pv3_voltage', 'pv3voltage', 'pv3_v'],
                'pv3_current': ['pv3_current', 'pv3current', 'pv3_c', 'pv3_i'],
                'pv3_power': ['pv3_power', 'pv3power', 'pv3_p', 'pv3_w'],
                'grid_voltage': ['grid_voltage', 'gridvoltage', 'grid_v', 'ac_voltage', 'acvoltage'],
                'grid_current': ['grid_current', 'gridcurrent', 'grid_c', 'grid_i', 'ac_current', 'accurrent'],
                'grid_power': ['grid_power', 'gridpower', 'grid_p', 'grid_w', 'ac_power', 'acpower'],
                'grid_frequency': ['grid_frequency', 'gridfrequency', 'grid_f', 'ac_frequency', 'acfrequency'],
                'temp': ['temp', 'temperature', 'inverter_temp', 'inverter_temperature'],
                'runtime_total': ['runtime_total', 'total_runtime', 'runtime', 'operating_time'],
                'energy_today': ['energy_today', 'today_energy', 'daily_energy', 'e_today'],
                'energy_total': ['energy_total', 'total_energy', 'e_total']
            }
            
            # Find actual column names in the database
            selected_columns = {}
            for std_name, alternatives in column_mapping.items():
                for alt in alternatives:
                    if alt in column_names:
                        selected_columns[std_name] = alt
                        break
            
            # Check if we have at least some essential columns
            essential_columns = ['grid_power', 'energy_today', 'energy_total']
            missing_essential = [col for col in essential_columns if col not in selected_columns]
            if missing_essential:
                logger.warning(f"Missing essential columns: {missing_essential}")
                
            # Construct the SELECT part of the query dynamically
            select_clauses = [f"id.{serial_column} as inverter_serial", f"id.{timestamp_column} as timestamp"]
            for std_name, db_name in selected_columns.items():
                select_clauses.append(f"id.{db_name} as {std_name}")
                
            # Add plant and device info
            select_clauses.extend([
                "d.alias as inverter_name",
                "d.type as inverter_type",
                "p.name as plant_name"
            ])
            
            select_statement = ",\n                ".join(select_clauses)
            
            # Build the complete query
            query = f"""
                SELECT 
                {select_statement}
                FROM 
                    inverter_details id
                JOIN
                    devices d ON id.{serial_column} = d.serial_number
                LEFT JOIN 
                    plants p ON d.plant_id = p.id
                WHERE 
                    id.{timestamp_column} BETWEEN %s AND %s
                ORDER BY 
                    id.{serial_column}, id.{timestamp_column}
            """
            
            logger.debug(f"Using dynamic query: {query}")
            
        except Exception as e:
            logger.warning(f"Could not retrieve column names: {e}")
            # Fall back to a guessed column structure
            serial_column = "serial_number"
            timestamp_column = "timestamp"
            logger.warning(f"Falling back to using '{serial_column}' as the serial number column and '{timestamp_column}' as the timestamp column")
            
            # Build a simple fallback query with common column names
            query = f"""
                SELECT 
                    id.{serial_column} as inverter_serial,
                    id.{timestamp_column} as timestamp,
                    id.pv1_voltage, id.pv1_current, id.pv1_power,
                    id.pv2_voltage, id.pv2_current, id.pv2_power,
                    id.pv3_voltage, id.pv3_current, id.pv3_power,
                    id.grid_voltage, id.grid_current, id.grid_power,
                    id.grid_frequency, id.temp, id.runtime_total,
                    id.energy_today, id.energy_total,
                    d.alias as inverter_name,
                    d.type as inverter_type,
                    p.name as plant_name
                FROM 
                    inverter_details id
                JOIN
                    devices d ON id.{serial_column} = d.serial_number
                LEFT JOIN 
                    plants p ON d.plant_id = p.id
                WHERE 
                    id.{timestamp_column} BETWEEN %s AND %s
                ORDER BY 
                    id.{serial_column}, id.{timestamp_column}
            """
        
        # Execute the query with error handling
        try:
            logger.info(f"Executing query for data between {start_date_str} and {end_date_str}")
            results = db.query(query, (start_date_str, end_date_str))
            
            if not results:
                logger.warning(f"No inverter data found for the period {start_date_str} to {end_date_str}")
                # Try a simpler query to check if the table has any data
                test_query = f"SELECT COUNT(*) FROM inverter_details"
                count_result = db.query(test_query)
                if count_result and count_result[0][0] > 0:
                    logger.info(f"The inverter_details table has {count_result[0][0]} records, but none match the date criteria.")
                    
                    # Debug: Get the min and max dates in the table
                    date_query = f"SELECT MIN({timestamp_column}), MAX({timestamp_column}) FROM inverter_details"
                    try:
                        date_result = db.query(date_query)
                        if date_result and date_result[0]:
                            min_date, max_date = date_result[0]
                            logger.info(f"Inverter data available from {min_date} to {max_date}")
                    except Exception as e:
                        logger.warning(f"Could not retrieve date range: {e}")
                else:
                    logger.warning("The inverter_details table appears to be empty.")
                return pd.DataFrame()
                
            # Convert to DataFrame
            df = pd.DataFrame(results)
            
            # Add appropriate column names if they weren't already set
            if len(df.columns) != len(select_clauses) and df.columns.dtype.kind == 'i':
                # Get the column names from the select statement
                column_names = []
                for clause in select_clauses:
                    # Extract the column alias or name after the last space or dot
                    parts = clause.strip().split(' as ')
                    if len(parts) > 1:
                        column_names.append(parts[-1].strip())
                    else:
                        # If there's no alias, use the part after the last dot
                        column_names.append(parts[0].strip().split('.')[-1])
                
                if len(df.columns) == len(column_names):
                    df.columns = column_names
                    logger.info("Assigned column names from the query")
                else:
                    logger.warning(f"Column count mismatch: {len(df.columns)} columns in DataFrame, {len(column_names)} names extracted")
            
            # Parse dates
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Convert numeric columns
            numeric_columns = [
                'pv1_voltage', 'pv1_current', 'pv1_power',
                'pv2_voltage', 'pv2_current', 'pv2_power',
                'pv3_voltage', 'pv3_current', 'pv3_power',
                'grid_voltage', 'grid_current', 'grid_power',
                'grid_frequency', 'temp', 'runtime_total',
                'energy_today', 'energy_total'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    logger.warning(f"Column '{col}' not found in the query results")
            
            logger.info(f"Fetched {len(df)} inverter records for {len(df['inverter_serial'].unique())} inverters")
            return df
            
        except Exception as e:
            logger.error(f"Unexpected error fetching inverter data: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            return pd.DataFrame()
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching inverter data: {e}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        return pd.DataFrame()

def generate_inverter_performance_plots(df: pd.DataFrame, output_dir: str) -> List[str]:
    """
    Generate plots showing inverter performance metrics
    
    Args:
        df: DataFrame containing inverter data
        output_dir: Directory to save plots
        
    Returns:
        List[str]: List of generated plot file paths
    """
    if df.empty:
        logger.warning("No data available to generate inverter performance plots")
        return []
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    plot_files = []
    
    try:
        # Set Seaborn style
        sns.set_style("whitegrid")
        
        # 1. Daily Energy Production
        plt.figure(figsize=(12, 6))
        
        # Group by date and sum energy_today
        daily_energy = df.copy()
        daily_energy['date'] = daily_energy['timestamp'].dt.date
        daily_energy = daily_energy.groupby('date')['energy_today'].sum().reset_index()
        daily_energy['date'] = pd.to_datetime(daily_energy['date'])
        
        sns.lineplot(data=daily_energy, x='date', y='energy_today', marker='o')
        plt.title('Daily Energy Production')
        plt.xlabel('Date')
        plt.ylabel('Energy Today (kWh)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        daily_energy_file = os.path.join(output_dir, 'daily_energy_production.png')
        plt.savefig(daily_energy_file)
        plt.close()
        plot_files.append(daily_energy_file)
        
        # 2. Energy Production by Inverter
        plt.figure(figsize=(12, 8))
        
        # Group by inverter and sum energy_today
        inverter_energy = df.groupby('inverter_name')['energy_today'].sum().sort_values(ascending=False)
        
        sns.barplot(x=inverter_energy.index, y=inverter_energy.values)
        plt.title('Total Energy Production by Inverter')
        plt.xlabel('Inverter')
        plt.ylabel('Total Energy (kWh)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        inverter_energy_file = os.path.join(output_dir, 'energy_by_inverter.png')
        plt.savefig(inverter_energy_file)
        plt.close()
        plot_files.append(inverter_energy_file)
        
        # 3. Energy Production by Plant
        plt.figure(figsize=(12, 8))
        
        # Group by plant and sum energy_today
        plant_energy = df.groupby('plant_name')['energy_today'].sum().sort_values(ascending=False)
        
        if not plant_energy.empty:
            sns.barplot(x=plant_energy.index, y=plant_energy.values)
            plt.title('Total Energy Production by Plant')
            plt.xlabel('Plant')
            plt.ylabel('Total Energy (kWh)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plant_energy_file = os.path.join(output_dir, 'energy_by_plant.png')
            plt.savefig(plant_energy_file)
            plt.close()
            plot_files.append(plant_energy_file)
            
        # 4. PV Power Comparison (PV1 vs PV2 vs PV3)
        plt.figure(figsize=(12, 8))
        
        # Calculate average power for each PV input
        pv_power = df.groupby('inverter_name')[['pv1_power', 'pv2_power', 'pv3_power']].mean().reset_index()
        pv_power = pv_power.melt(id_vars='inverter_name', var_name='PV Input', value_name='Average Power (W)')
        
        # Plot the comparison
        sns.barplot(data=pv_power, x='inverter_name', y='Average Power (W)', hue='PV Input')
        plt.title('Average PV Power by Input')
        plt.xlabel('Inverter')
        plt.ylabel('Average Power (W)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        pv_comparison_file = os.path.join(output_dir, 'pv_power_comparison.png')
        plt.savefig(pv_comparison_file)
        plt.close()
        plot_files.append(pv_comparison_file)
        
        # 5. Temperature Distribution
        plt.figure(figsize=(10, 6))
        
        # Calculate average temperature for each inverter
        temp_data = df.groupby('inverter_name')['temp'].mean().sort_values(ascending=False)
        
        sns.barplot(x=temp_data.index, y=temp_data.values)
        plt.title('Average Temperature by Inverter')
        plt.xlabel('Inverter')
        plt.ylabel('Temperature (°C)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        temp_file = os.path.join(output_dir, 'temperature_distribution.png')
        plt.savefig(temp_file)
        plt.close()
        plot_files.append(temp_file)
        
        logger.info(f"Generated {len(plot_files)} inverter performance plots")
        return plot_files
        
    except Exception as e:
        logger.error(f"Error generating inverter performance plots: {e}")
        return plot_files

def generate_power_trend_plots(df: pd.DataFrame, output_dir: str) -> List[str]:
    """
    Generate plots showing power trends over time
    
    Args:
        df: DataFrame containing inverter data
        output_dir: Directory to save plots
        
    Returns:
        List[str]: List of generated plot file paths
    """
    if df.empty:
        logger.warning("No data available to generate power trend plots")
        return []
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    plot_files = []
    
    try:
        # Set Seaborn style
        sns.set_style("whitegrid")
        
        # Group data by hour for daily patterns
        df['hour'] = df['timestamp'].dt.hour
        hourly_power = df.groupby('hour')['grid_power'].mean().reset_index()
        
        # 1. Daily Power Pattern
        plt.figure(figsize=(12, 6))
        sns.lineplot(data=hourly_power, x='hour', y='grid_power', marker='o')
        plt.title('Average Power Output by Hour of Day')
        plt.xlabel('Hour of Day')
        plt.ylabel('Average Grid Power (W)')
        plt.xticks(range(0, 24))
        plt.grid(True)
        plt.tight_layout()
        hourly_power_file = os.path.join(output_dir, 'daily_power_pattern.png')
        plt.savefig(hourly_power_file)
        plt.close()
        plot_files.append(hourly_power_file)
        
        # Get top 5 inverters by total energy
        top_inverters = df.groupby('inverter_serial')['energy_total'].max().sort_values(ascending=False).head(5).index.tolist()
        
        # 2. Power Output Over Time for Top Inverters
        plt.figure(figsize=(14, 8))
        
        for inverter in top_inverters:
            inverter_df = df[df['inverter_serial'] == inverter]
            if not inverter_df.empty:
                inverter_name = inverter_df['inverter_name'].iloc[0]
                # Create a daily summary for smoother visualization
                inverter_daily = inverter_df.groupby(inverter_df['timestamp'].dt.date)['grid_power'].mean().reset_index()
                inverter_daily['timestamp'] = pd.to_datetime(inverter_daily['timestamp'])
                plt.plot(inverter_daily['timestamp'], inverter_daily['grid_power'], marker='o', linestyle='-', label=inverter_name)
        
        plt.title('Average Daily Power Output for Top Inverters')
        plt.xlabel('Date')
        plt.ylabel('Average Grid Power (W)')
        plt.legend(title='Inverter')
        plt.grid(True)
        plt.tight_layout()
        power_time_file = os.path.join(output_dir, 'power_output_over_time.png')
        plt.savefig(power_time_file)
        plt.close()
        plot_files.append(power_time_file)
        
        # 3. PV Power vs. Grid Power
        # Get the most recent data point for each inverter
        latest_data = df.sort_values('timestamp').groupby('inverter_serial').last().reset_index()
        
        plt.figure(figsize=(12, 8))
        latest_data['total_pv_power'] = latest_data['pv1_power'] + latest_data['pv2_power'] + latest_data['pv3_power']
        latest_data['efficiency'] = np.where(latest_data['total_pv_power'] > 0, 
                                            latest_data['grid_power'] / latest_data['total_pv_power'] * 100, 
                                            0)
        
        # Filter out invalid efficiency values
        latest_data = latest_data[(latest_data['efficiency'] <= 100) & (latest_data['efficiency'] > 0)]
        
        plt.scatter(latest_data['total_pv_power'], latest_data['grid_power'], alpha=0.7, s=100)
        
        # Add inverter names as annotations
        for i, row in latest_data.iterrows():
            plt.annotate(row['inverter_name'], 
                        (row['total_pv_power'], row['grid_power']),
                        xytext=(5, 5),
                        textcoords='offset points')
        
        # Add diagonal line for 100% efficiency
        max_power = max(latest_data['total_pv_power'].max(), latest_data['grid_power'].max())
        plt.plot([0, max_power], [0, max_power], 'r--', alpha=0.5, label='100% Efficiency')
        
        plt.title('PV Input Power vs Grid Output Power')
        plt.xlabel('Total PV Input Power (W)')
        plt.ylabel('Grid Output Power (W)')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        efficiency_file = os.path.join(output_dir, 'power_efficiency.png')
        plt.savefig(efficiency_file)
        plt.close()
        plot_files.append(efficiency_file)
        
        # 4. Energy Histogram
        plt.figure(figsize=(12, 6))
        
        # Daily energy distribution
        daily_inverter_energy = df.copy()
        daily_inverter_energy['date'] = daily_inverter_energy['timestamp'].dt.date
        daily_inverter_energy = daily_inverter_energy.groupby(['inverter_name', 'date'])['energy_today'].max().reset_index()
        
        sns.histplot(data=daily_inverter_energy, x='energy_today', bins=20, kde=True)
        plt.title('Distribution of Daily Energy Production')
        plt.xlabel('Daily Energy (kWh)')
        plt.ylabel('Frequency')
        plt.grid(True)
        plt.tight_layout()
        energy_hist_file = os.path.join(output_dir, 'energy_distribution.png')
        plt.savefig(energy_hist_file)
        plt.close()
        plot_files.append(energy_hist_file)
        
        logger.info(f"Generated {len(plot_files)} power trend plots")
        return plot_files
        
    except Exception as e:
        logger.error(f"Error generating power trend plots: {e}")
        return plot_files

def generate_pdf_report(
    df: pd.DataFrame, 
    performance_plots: List[str], 
    trend_plots: List[str],
    days: int
) -> str:
    """
    Generate a PDF report from the inverter data and plots
    
    Args:
        df: DataFrame containing inverter data
        performance_plots: List of inverter performance plot file paths
        trend_plots: List of power trend plot file paths
        days: Number of days the report covers
        
    Returns:
        str: Path to the generated PDF file
    """
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(reports_dir, f"inverter_report_{timestamp}.pdf")
    
    try:
        # Create PDF
        with PdfPages(pdf_path) as pdf:
            # Title page
            plt.figure(figsize=(12, 8))
            plt.axis('off')
            plt.text(0.5, 0.8, "Growatt Inverter Performance Report", fontsize=24, ha='center')
            plt.text(0.5, 0.7, f"Report Period: Last {days} Days", fontsize=18, ha='center')
            plt.text(0.5, 0.6, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=14, ha='center')
            
            # Inverter stats
            if not df.empty:
                total_inverters = len(df['inverter_serial'].unique())
                total_energy = df['energy_today'].sum()
                total_plants = len(df['plant_name'].unique())
                plt.text(0.5, 0.4, f"Total Inverters: {total_inverters}", fontsize=14, ha='center')
                plt.text(0.5, 0.35, f"Total Energy Production: {total_energy:.2f} kWh", fontsize=14, ha='center')
                plt.text(0.5, 0.3, f"Total Plants: {total_plants}", fontsize=14, ha='center')
            
            plt.tight_layout()
            pdf.savefig()
            plt.close()
            
            # Add performance plots
            for plot_file in performance_plots:
                if os.path.exists(plot_file):
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    img = plt.imread(plot_file)
                    plt.imshow(img)
                    plt.tight_layout()
                    pdf.savefig()
                    plt.close()
            
            # Add trend plots
            for plot_file in trend_plots:
                if os.path.exists(plot_file):
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    img = plt.imread(plot_file)
                    plt.imshow(img)
                    plt.tight_layout()
                    pdf.savefig()
                    plt.close()
            
            # Add inverter summary table
            if not df.empty:
                # Get the latest data for each inverter
                latest_data = df.sort_values('timestamp').groupby('inverter_serial').last()
                
                # Calculate efficiency
                latest_data['total_pv_power'] = latest_data['pv1_power'] + latest_data['pv2_power'] + latest_data['pv3_power']
                latest_data['efficiency'] = np.where(latest_data['total_pv_power'] > 0, 
                                                  latest_data['grid_power'] / latest_data['total_pv_power'] * 100, 
                                                  0)
                latest_data['efficiency'] = latest_data['efficiency'].clip(0, 100)
                
                # Prepare summary table
                summary = latest_data.reset_index()[['inverter_serial', 'inverter_name', 'plant_name', 
                                                   'grid_power', 'total_pv_power', 'efficiency', 
                                                   'energy_today', 'energy_total', 'temp']]
                
                summary.columns = ['Serial Number', 'Name', 'Plant', 'Grid Power (W)', 
                                 'PV Power (W)', 'Efficiency (%)', 'Energy Today (kWh)', 
                                 'Total Energy (kWh)', 'Temperature (°C)']
                
                # Round numeric values for better display
                for col in ['Grid Power (W)', 'PV Power (W)', 'Efficiency (%)', 
                           'Energy Today (kWh)', 'Total Energy (kWh)', 'Temperature (°C)']:
                    summary[col] = summary[col].round(2)
                
                # Sort by energy today
                summary = summary.sort_values('Energy Today (kWh)', ascending=False)
                
                # Split into chunks for the table
                chunk_size = 10
                for i in range(0, len(summary), chunk_size):
                    chunk = summary.iloc[i:i+chunk_size]
                    
                    # Create a figure
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    plt.title('Inverter Summary', fontsize=18)
                    
                    # Create the table
                    table = plt.table(
                        cellText=chunk.values,
                        colLabels=chunk.columns,
                        cellLoc='center',
                        loc='center',
                        bbox=[0.0, 0.0, 1.0, 1.0]
                    )
                    
                    # Style the table
                    table.auto_set_font_size(False)
                    table.set_fontsize(8)
                    table.scale(1, 1.5)
                    
                    pdf.savefig()
                    plt.close()
            
            # Add detailed PV input data
            if not df.empty:
                # Prepare PV input summary
                pv_summary = latest_data.reset_index()[['inverter_serial', 'inverter_name', 
                                                      'pv1_voltage', 'pv1_current', 'pv1_power',
                                                      'pv2_voltage', 'pv2_current', 'pv2_power',
                                                      'pv3_voltage', 'pv3_current', 'pv3_power']]
                
                pv_summary.columns = ['Serial Number', 'Name', 
                                    'PV1 Voltage (V)', 'PV1 Current (A)', 'PV1 Power (W)',
                                    'PV2 Voltage (V)', 'PV2 Current (A)', 'PV2 Power (W)',
                                    'PV3 Voltage (V)', 'PV3 Current (A)', 'PV3 Power (W)']
                
                # Round numeric values
                for col in pv_summary.columns[2:]:
                    pv_summary[col] = pv_summary[col].round(2)
                
                # Sort by inverter name
                pv_summary = pv_summary.sort_values('Name')
                
                # Split into chunks for the table
                chunk_size = 10
                for i in range(0, len(pv_summary), chunk_size):
                    chunk = pv_summary.iloc[i:i+chunk_size]
                    
                    # Create a figure
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    plt.title('PV Input Details', fontsize=18)
                    
                    # Create the table
                    table = plt.table(
                        cellText=chunk.values,
                        colLabels=chunk.columns,
                        cellLoc='center',
                        loc='center',
                        bbox=[0.0, 0.0, 1.0, 1.0]
                    )
                    
                    # Style the table
                    table.auto_set_font_size(False)
                    table.set_fontsize(8)
                    table.scale(1, 1.5)
                    
                    pdf.savefig()
                    plt.close()
        
        logger.info(f"Generated PDF report at {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        return ""

def send_email(pdf_path: str, recipient: Union[str, List[str]]) -> bool:
    """
    Send the PDF report via email
    
    Args:
        pdf_path: Path to the PDF report
        recipient: Email address or list of addresses to send the report to
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Process recipient (can be string or list)
    # Convert string input that looks like a list to an actual list
    if isinstance(recipient, str) and recipient.startswith('[') and recipient.endswith(']'):
        try:
            # This handles cases where the recipient is a string like '["email@example.com"]'
            # Strip the outer quotes and brackets, then split by comma
            cleaned = recipient.strip('[]').replace('"', '').replace("'", "")
            recipient_list = [email.strip() for email in cleaned.split(',') if email.strip()]
            if recipient_list:
                recipient = recipient_list
            else:
                logger.error(f"Failed to parse recipient list from string: {recipient}")
        except Exception as e:
            logger.warning(f"Error parsing recipient string as list: {e}. Will treat as a regular string.")
    
    # Now handle the recipient appropriately based on its type
    if isinstance(recipient, list):
        if not recipient:
            logger.error("Empty recipient list provided")
            return False
        # For SMTP, we'll use all emails in the list
        email_recipients = recipient
        # For the 'To' header, join with commas
        email_recipient_header = ', '.join(recipient)
    else:
        email_recipients = [recipient]  # Convert to list for consistent handling
        email_recipient_header = recipient
        
    if not email_recipients:
        logger.error("No recipient email provided")
        return False
    try:
        from app.config import Config
        
        # Check if email is enabled
        if not Config.EMAIL_NOTIFICATIONS_ENABLED:
            logger.error("Email notifications are not enabled in configuration")
            return False
            
        # Check if PDF exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file does not exist: {pdf_path}")
            return False
        
        # Log SMTP configuration for debugging
        smtp_server = Config.SMTP_SERVER
        smtp_port = Config.SMTP_PORT
        smtp_user = Config.SMTP_USERNAME
        smtp_use_tls = Config.SMTP_USE_TLS
        
        # Don't log the actual password, just whether it's set
        has_smtp_password = bool(Config.SMTP_PASSWORD)
        
        logger.info(f"SMTP Configuration: Server={smtp_server}, Port={smtp_port}, "
                   f"User={smtp_user}, TLS={smtp_use_tls}, Password set={has_smtp_password}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_FROM
        msg['To'] = email_recipient_header
        msg['Subject'] = f"Growatt Inverter Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = """
        <html>
            <body>
                <h2>Growatt Inverter Performance Report</h2>
                <p>Please find attached the inverter performance report with data visualizations.</p>
                <p>This report includes detailed inverter metrics, power production data, and efficiency analysis.</p>
                <p>The report was automatically generated on {datetime}.</p>
                <p>Best regards,<br>
                Growatt Monitoring System</p>
            </body>
        </html>
        """.format(datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach PDF
        with open(pdf_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), _subtype='pdf')
            attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(attachment)
        
        # Connect to SMTP server and send email
        try:
            logger.info(f"Connecting to SMTP server: {smtp_server}:{smtp_port}")
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                # Enable debug output for SMTP connection
                server.set_debuglevel(1)
                
                if smtp_use_tls:
                    logger.info("Starting TLS connection")
                    server.starttls()
                
                # Only attempt login if both username and password are provided
                if smtp_user and has_smtp_password:
                    logger.info(f"Logging in with username: {smtp_user}")
                    try:
                        server.login(smtp_user, Config.SMTP_PASSWORD)
                        logger.info("SMTP login successful")
                    except smtplib.SMTPAuthenticationError as auth_err:
                        if "Username and Password not accepted" in str(auth_err):
                            logger.error(f"SMTP authentication failed: {auth_err}")
                            logger.error("Gmail users: Make sure to use an App Password instead of your regular password. "
                                        "See https://support.google.com/accounts/answer/185833 for instructions.")
                        else:
                            logger.error(f"SMTP authentication error: {auth_err}")
                        return False
                
                logger.info(f"Sending email from {Config.EMAIL_FROM} to {email_recipient_header}")
                server.send_message(msg)
                logger.info("Email sent successfully")
            
            logger.info(f"Sent report email to {email_recipient_header}")
            return True
            
        except smtplib.SMTPConnectError as conn_err:
            logger.error(f"Failed to connect to SMTP server: {conn_err}")
            return False
        except smtplib.SMTPServerDisconnected as disc_err:
            logger.error(f"SMTP server disconnected: {disc_err}")
            return False
        except smtplib.SMTPException as smtp_err:
            logger.error(f"SMTP error: {smtp_err}")
            return False
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def send_telegram(pdf_path: str) -> bool:
    """
    Send the PDF report via Telegram
    
    Args:
        pdf_path: Path to the PDF report
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        from app.config import Config
        
        # Check if Telegram integration is enabled
        if not hasattr(Config, 'TELEGRAM_ENABLED') or not Config.TELEGRAM_ENABLED:
            logger.error("Telegram notifications are not enabled in configuration")
            return False
            
        # Check if PDF exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file does not exist: {pdf_path}")
            return False
        
        # Get Telegram bot token and chat ID
        if not hasattr(Config, 'TELEGRAM_BOT_TOKEN') or not Config.TELEGRAM_BOT_TOKEN:
            logger.error("Telegram bot token not configured")
            return False
            
        if not hasattr(Config, 'TELEGRAM_CHAT_ID') or not Config.TELEGRAM_CHAT_ID:
            logger.error("Telegram chat ID not configured")
            return False
            
        bot_token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID
        
        # Prepare API URLs
        base_url = f"https://api.telegram.org/bot{bot_token}"
        send_message_url = f"{base_url}/sendMessage"
        send_document_url = f"{base_url}/sendDocument"
        
        # Send text message first
        message_text = f"""
📊 *Growatt Inverter Performance Report*
        
A new inverter report has been generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

This report includes:
- Inverter performance metrics
- Power production data
- Efficiency analysis
- PV input details

The report is attached below.
        """
        
        message_payload = {
            'chat_id': chat_id,
            'text': message_text,
            'parse_mode': 'Markdown'
        }
        
        # Send message
        try:
            message_response = requests.post(send_message_url, json=message_payload)
            message_response.raise_for_status()
            logger.info("Telegram text message sent successfully")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Failed to send Telegram message: {req_err}")
            return False
        
        # Send PDF document
        with open(pdf_path, 'rb') as pdf_file:
            files = {'document': (os.path.basename(pdf_path), pdf_file, 'application/pdf')}
            document_payload = {
                'chat_id': chat_id,
                'caption': 'Inverter Performance Report'
            }
            
            try:
                document_response = requests.post(send_document_url, data=document_payload, files=files)
                document_response.raise_for_status()
                logger.info("Telegram PDF document sent successfully")
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Failed to send Telegram document: {req_err}")
                return False
        
        logger.info(f"Successfully sent report via Telegram to chat ID: {chat_id}")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def main():
    """
    Main function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate inverter report with visualizations and send via email/Telegram")
    parser.add_argument("--days", type=int, default=7, help="Number of days to include in the report")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--email", type=str, help="Email address to send report to (if not specified, uses the default from config)")
    parser.add_argument("--telegram", action="store_true", help="Send report via Telegram")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        logger.info("Starting inverter report generation")
        
        # Create temporary directory for plots
        temp_dir = os.path.join("reports", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Fetch data
        logger.info(f"Fetching inverter data for the last {args.days} days")
        inverter_df = fetch_inverter_data(args.days)
        
        if inverter_df.empty:
            logger.error("No inverter data available to generate report")
            return 1
            
        # Generate plots
        logger.info("Generating inverter performance plots")
        performance_plots = generate_inverter_performance_plots(inverter_df, temp_dir)
        
        logger.info("Generating power trend plots")
        trend_plots = generate_power_trend_plots(inverter_df, temp_dir)
        
        # Generate PDF report
        logger.info("Generating PDF report")
        pdf_path = generate_pdf_report(inverter_df, performance_plots, trend_plots, args.days)
        
        if not pdf_path:
            logger.error("Failed to generate PDF report")
            return 1
            
        # Send email if requested
        if args.email:
            logger.info(f"Sending report to {args.email}")
            email_success = send_email(pdf_path, args.email)
            
            if not email_success:
                logger.error("Failed to send email")
                # Continue with execution, don't return error yet
        else:
            # Try to get default email from config
            try:
                from app.config import Config
                if hasattr(Config, 'EMAIL_TO') and Config.EMAIL_TO:
                    logger.info(f"Sending report to default email: {Config.EMAIL_TO}")
                    email_success = send_email(pdf_path, Config.EMAIL_TO)
                    
                    if not email_success:
                        logger.error("Failed to send email to default address")
                        logger.info(f"Report generated at {pdf_path}")
                else:
                    logger.info(f"No email address specified and no default found. Report generated at {pdf_path}")
            except Exception as e:
                logger.info(f"Could not determine default email: {e}. Report generated at {pdf_path}")
        
        # Send via Telegram if requested
        if args.telegram:
            logger.info("Sending report via Telegram")
            telegram_success = send_telegram(pdf_path)
            
            if not telegram_success:
                logger.error("Failed to send via Telegram")
                # Continue with execution, don't return error yet
        
        # Clean up temporary files
        for plot_file in performance_plots + trend_plots:
            try:
                os.remove(plot_file)
            except Exception as e:
                logger.debug(f"Could not remove plot file {plot_file}: {e}")
                
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            logger.debug(f"Could not remove temp directory: {e}")
            
        logger.info("Inverter report generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in inverter report generation: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
