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
import traceback
import re

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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Add diagnostic output for PATH
logger.debug(f"Python path: {sys.path}")

# Check if critical modules are available
try:
    from app.database import DatabaseConnector
    logger.debug("Successfully imported DatabaseConnector")
except ImportError as e:
    logger.critical(f"Failed to import DatabaseConnector: {e}")
    logger.critical("Please make sure the app module is in your Python path")
    
try:
    from app.config import Config
    logger.debug("Successfully imported Config")
except ImportError as e:
    logger.critical(f"Failed to import Config: {e}")
    logger.critical("Please make sure the app module is in your Python path")

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

def ensure_thai_font_support():
    """
    Make sure Thai font support is properly configured for matplotlib
    This function should be called before creating any plots
    """
    global registered_fonts
    
    # If we already have registered fonts, no need to check again
    if registered_fonts:
        return
    
    # Try to register fonts again if they weren't found initially
    # This is a more aggressive attempt to find any font with Thai support
    logger.info("Ensuring Thai font support for plots")
    
    # Common locations for fonts with Thai support
    additional_font_paths = [
        # System fonts
        '/usr/share/fonts',
        '/usr/local/share/fonts',
        os.path.expanduser('~/.fonts'),
        os.path.expanduser('~/Library/Fonts'),
        # Look for fonts in the project's font directory
        os.path.join(project_root, 'fonts')
    ]
    
    # Try to find any font with Thai support
    for font_dir in additional_font_paths:
        if os.path.exists(font_dir):
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                        try:
                            font_path = os.path.join(root, file)
                            # Register the font with matplotlib
                            font_prop = fm.FontProperties(fname=font_path)
                            registered_fonts.append(font_prop)
                            font_name = font_prop.get_name()
                            matplotlib.font_manager.fontManager.addfont(font_path)
                            logger.debug(f"Registered additional font: {font_path}")
                        except Exception as e:
                            # Skip fonts that can't be loaded
                            pass
    
    # Set a good default if any fonts were found
    if registered_fonts and not plt.rcParams.get('font.family', None):
        plt.rcParams['font.family'] = registered_fonts[0].get_name()
        logger.info(f"Using {plt.rcParams['font.family']} as primary font")
    else:
        # Last resort: Use a generic sans-serif font
        logger.warning("Using system default fonts. Thai characters may not display correctly.")
        plt.rcParams['font.family'] = 'sans-serif'

def ensure_thai_text_display(text):
    """
    Ensure text with Thai characters is properly displayed
    If the text contains Thai characters but can't be displayed,
    replace it with a readable numeric identifier
    
    Args:
        text: Input text that might contain Thai characters
        
    Returns:
        str: Text ready for display
    """
    if not text:
        return ""
    
    # Check if the text contains Thai characters
    thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
    has_thai = bool(thai_pattern.search(str(text)))
    
    if not has_thai:
        return text
    
    # If we have Thai text, check if we have font support
    if not registered_fonts:
        # Extract a numeric ID from the text using different common patterns
        
        # Pattern 1: ID in parentheses - "Plant Name (ID: 12345)" or "Plant Name (12345)"
        id_match = re.search(r'\(\s*(?:ID:?)?\s*(\d+)\s*\)', str(text))
        if id_match:
            return f"ID-{id_match.group(1)}"
        
        # Pattern 2: ID after hash - "Plant Name #12345"
        id_match = re.search(r'#\s*(\d+)', str(text))
        if id_match:
            return f"ID-{id_match.group(1)}"
        
        # Pattern 3: ID after colon or dash - "Plant Name: 12345" or "Plant Name - 12345"
        id_match = re.search(r'[:|-]\s*(\d+)', str(text))
        if id_match:
            return f"ID-{id_match.group(1)}"
        
        # Pattern 4: Just extract any number sequence as last resort
        id_match = re.search(r'(\d+)', str(text))
        if id_match:
            return f"ID-{id_match.group(1)}"
        
        # If no numeric ID found, provide a consistent hash-based ID
        import hashlib
        hash_object = hashlib.md5(str(text).encode())
        short_hash = hash_object.hexdigest()[:6]
        return f"Plant-{short_hash}"
    
    # We have Thai fonts registered, so return the original text
    return text

def extract_numeric_id(name_series):
    """
    Extract numeric IDs from a series of names
    Used for consistent labeling when displaying Thai text
    
    Args:
        name_series: pandas Series containing names that might have Thai characters
        
    Returns:
        pd.Series: Series with extracted IDs or original values if no IDs found
    """
    def extract_id(text):
        if not text or not isinstance(text, str):
            return text
            
        # Pattern 1: ID in parentheses
        id_match = re.search(r'\(\s*(?:ID:?)?\s*(\d+)\s*\)', text)
        if id_match:
            return id_match.group(1)
        
        # Pattern 2: ID after hash
        id_match = re.search(r'#\s*(\d+)', text)
        if id_match:
            return id_match.group(1)
        
        # Pattern 3: ID after colon or dash
        id_match = re.search(r'[:|-]\s*(\d+)', text)
        if id_match:
            return id_match.group(1)
        
        # Pattern 4: Just any number as last resort
        id_match = re.search(r'(\d+)', text)
        if id_match:
            return id_match.group(1)
            
        return text
        
    return name_series.apply(extract_id)

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
        
        # Query to fetch inverter data
        query = f"""
            SELECT 
                inv.serial_number as inverter_serial,
                inv.collected_at as timestamp,
                inv.energy_today,
                inv.energy_total,
                inv.grid_voltage,
                inv.grid_current,
                inv.grid_power,
                inv.grid_frequency,
                inv.temp as temperature,
                d.alias as inverter_name,
                d.type as inverter_type,
                p.name as plant_name
            FROM 
                inverter_details inv
            JOIN 
                devices d ON inv.serial_number = d.serial_number
            LEFT JOIN 
                plants p ON d.plant_id = p.id
            WHERE 
                inv.collected_at BETWEEN %s AND %s
            ORDER BY 
                inv.serial_number, inv.collected_at
        """
        
        # Execute the query
        results = db.query(query, (start_date_str, end_date_str))
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Set column names
        df.columns = [
            'inverter_serial', 'timestamp', 'energy_today', 'energy_total',
            'grid_voltage', 'grid_current', 'grid_power', 'grid_frequency',
            'temperature', 'inverter_name', 'inverter_type', 'plant_name'
        ]
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Convert numeric columns
        numeric_cols = ['energy_today', 'energy_total', 'grid_voltage', 'grid_current', 'grid_power', 'grid_frequency', 'temperature']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching inverter data: {e}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def generate_inverter_performance_plots(df: pd.DataFrame, output_dir: str) -> List[str]:
    """
    Generate enhanced plots showing inverter performance metrics with improved visual appeal
    and data insights.
    
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
        # Ensure Thai fonts are properly set before plotting
        ensure_thai_font_support()
        
        # Pre-process plant and inverter names for better display
        if 'plant_name' in df.columns:
            # First, try to extract numeric IDs for consistent labeling
            df['plant_id'] = extract_numeric_id(df['plant_name'])
            # Then create display-friendly versions
            df['plant_name_display'] = df['plant_name'].apply(ensure_thai_text_display)
            
        if 'inverter_name' in df.columns:
            # Do the same for inverter names
            df['inverter_id'] = extract_numeric_id(df['inverter_name'])
            df['inverter_name_display'] = df['inverter_name'].apply(ensure_thai_text_display)
        
        # Set up improved visual style
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['figure.facecolor'] = '#f9f9f9'
        plt.rcParams['axes.facecolor'] = '#f9f9f9'
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.color'] = '#e0e0e0'
        plt.rcParams['grid.linestyle'] = '-'
        plt.rcParams['axes.spines.top'] = False
        plt.rcParams['axes.spines.right'] = False
        
        # Define a color palette
        colors = plt.cm.viridis(np.linspace(0, 1, 10))
        color_main = '#1f77b4'  # Primary color
        color_accent = '#ff7f0e'  # Accent color
        
        # 1. Daily Energy Production with trend line and highlighting weekends
        plt.figure(figsize=(14, 7))
        
        # Group by date and sum energy_today
        daily_energy = df.copy()
        daily_energy['date'] = daily_energy['timestamp'].dt.date
        daily_energy = daily_energy.groupby('date')['energy_today'].sum().reset_index()
        daily_energy['date'] = pd.to_datetime(daily_energy['date'])
        
        # Add day of week information
        daily_energy['day_of_week'] = daily_energy['date'].dt.day_name()
        daily_energy['is_weekend'] = daily_energy['day_of_week'].isin(['Saturday', 'Sunday'])
        
        # Plot weekdays and weekends with different colors
        weekday_data = daily_energy[~daily_energy['is_weekend']]
        weekend_data = daily_energy[daily_energy['is_weekend']]
        
        plt.scatter(weekday_data['date'], weekday_data['energy_today'], 
                   s=80, color=color_main, alpha=0.7, label='Weekday')
        plt.scatter(weekend_data['date'], weekend_data['energy_today'], 
                   s=80, color=color_accent, alpha=0.7, label='Weekend')
        
        # Add smooth trend line
        if len(daily_energy) > 3:  # Only add trend if we have enough data
            try:
                from scipy.signal import savgol_filter
                if len(daily_energy) >= 7:  # At least a week of data
                    yhat = savgol_filter(daily_energy['energy_today'], 
                                        min(7, len(daily_energy) - (len(daily_energy) % 2 or 1)), 
                                        3)
                    plt.plot(daily_energy['date'], yhat, color='#d62728', 
                            linewidth=2, alpha=0.8, label='Trend')
            except ImportError:
                # If scipy is not available, use a simple moving average
                daily_energy['ma'] = daily_energy['energy_today'].rolling(window=3, min_periods=1).mean()
                plt.plot(daily_energy['date'], daily_energy['ma'], color='#d62728', 
                        linewidth=2, alpha=0.8, label='3-day Moving Avg')
        
        # Add average line
        avg_energy = daily_energy['energy_today'].mean()
        plt.axhline(y=avg_energy, color='#9467bd', linestyle='--', alpha=0.7, 
                   label=f'Avg: {avg_energy:.2f} kWh')
        
        # Calculate statistics to display
        total_energy = daily_energy['energy_today'].sum()
        max_energy = daily_energy['energy_today'].max()
        max_date = daily_energy.loc[daily_energy['energy_today'].idxmax()]['date']
        
        # Add annotations
        plt.annotate(f'Max: {max_energy:.2f} kWh on {max_date.strftime("%Y-%m-%d")}', 
                    xy=(max_date, max_energy), xytext=(10, 10),
                    textcoords='offset points', color='#d62728', fontweight='bold')
        
        plt.title('Daily Energy Production Over Time', fontsize=16, pad=20)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Energy Production (kWh)', fontsize=12)
        plt.xticks(rotation=45)
        plt.legend(loc='upper left', frameon=True)
        
        # Add text with statistics
        plt.figtext(0.02, 0.02, 
                   f'Total Energy: {total_energy:.2f} kWh | Daily Average: {avg_energy:.2f} kWh | Max: {max_energy:.2f} kWh', 
                   fontsize=10, wrap=True)
        
        plt.tight_layout()
        daily_energy_file = os.path.join(output_dir, 'daily_energy_production.png')
        plt.savefig(daily_energy_file, dpi=120)
        plt.close()
        plot_files.append(daily_energy_file)
        
        # 2. Energy Production by Inverter (Use inverter_name_display for better Thai support)
        plt.figure(figsize=(14, max(8, min(20, len(df['inverter_name_display'].unique()) * 0.5))))
        
        # Group by inverter and sum energy_today
        inverter_name_col = 'inverter_name_display' if 'inverter_name_display' in df.columns else 'inverter_name'
        inverter_energy = df.groupby(inverter_name_col)['energy_today'].sum().sort_values(ascending=True)
        
        # Limit number of inverters displayed to avoid overcrowding
        if len(inverter_energy) > 20:
            logger.info(f"Limiting inverter chart to top 20 out of {len(inverter_energy)} inverters")
            inverter_energy = inverter_energy.tail(20)  # Take the top 20 by energy (already sorted ascending)
            
        total = inverter_energy.sum()
        
        # Calculate percentages
        percentages = [f"{(v/total*100):.1f}%" for v in inverter_energy.values]
        
        # Create horizontal bar chart
        ax = sns.barplot(y=inverter_energy.index, x=inverter_energy.values, palette='viridis')
        
        # Add value labels
        for i, (val, pct) in enumerate(zip(inverter_energy.values, percentages)):
            ax.text(val + (total * 0.01), i, f"{val:.2f} kWh ({pct})", va='center', fontweight='bold')
        
        plt.title('Energy Production by Inverter', fontsize=16, pad=20)
        plt.xlabel('Total Energy (kWh)', fontsize=12)
        plt.ylabel('Inverter', fontsize=12)
        plt.tight_layout()
        inverter_energy_file = os.path.join(output_dir, 'energy_by_inverter.png')
        plt.savefig(inverter_energy_file, dpi=120)
        plt.close()
        plot_files.append(inverter_energy_file)
        
        # 3. Energy Production by Plant with percentage and count information
        if 'plant_name' in df.columns:
            # Check if we have any valid plant data
            valid_plants = df['plant_name'].dropna().astype(str)
            valid_plants = valid_plants[valid_plants.str.strip() != '']
            
            if len(valid_plants) == 0:
                logger.warning("No valid plant names found in data, skipping plant charts")
            else:
                # Use display-friendly names for plants
                plant_name_col = 'plant_name_display' if 'plant_name_display' in df.columns else 'plant_name'
                
                # Replace any remaining NaN values with a placeholder
                df[plant_name_col] = df[plant_name_col].fillna('Unknown Plant')
                
                # Group by plant
                try:
                    plant_counts = df.groupby(plant_name_col)['inverter_serial'].nunique()
                    plant_energy = df.groupby(plant_name_col)['energy_today'].sum().sort_values(ascending=False)
                    
                    # Limit number of plants displayed to avoid overcrowding
                    if len(plant_energy) > 15:
                        logger.info(f"Limiting plant chart to top 15 out of {len(plant_energy)} plants")
                        plant_energy = plant_energy.head(15)
                        plant_counts = plant_counts.reindex(plant_energy.index)
                    
                    if not plant_energy.empty:
                        plt.figure(figsize=(14, max(8, min(15, len(plant_energy) * 0.8))))
                        
                        # Create the bar chart
                        ax = sns.barplot(x=plant_energy.index, y=plant_energy.values, palette='viridis')
                        
                        # Add percentage and count annotations
                        total_energy = plant_energy.sum()
                        for i, (plant, energy) in enumerate(plant_energy.items()):
                            percentage = energy / total_energy * 100
                            count = plant_counts.get(plant, 0)  # Use get with default to handle missing keys
                            ax.text(i, energy + total_energy * 0.02, 
                                   f"{energy:.2f} kWh\n({percentage:.1f}%)\n{count} inverter{'s' if count > 1 else ''}", 
                                   ha='center', fontweight='bold')
                        
                        plt.title('Energy Production by Plant', fontsize=16, pad=20)
                        plt.xlabel('Plant', fontsize=12)
                        plt.ylabel('Total Energy (kWh)', fontsize=12)
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        plant_energy_file = os.path.join(output_dir, 'energy_by_plant.png')
                        plt.savefig(plant_energy_file, dpi=120)
                        plt.close()
                        plot_files.append(plant_energy_file)
                        
                        # Log generated plant data for debugging
                        logger.debug(f"Generated plant chart with {len(plant_energy)} plants")
                        logger.debug(f"Plant names: {', '.join(plant_energy.index.astype(str))}")
                except Exception as e:
                    logger.error(f"Error generating plant energy chart: {e}")
                    logger.error(traceback.format_exc())
        else:
            logger.warning("No plant_name column in data, skipping plant charts")
        
        # 4. Add a simple table view of plants and inverters as an additional visualization
        # This is a good fallback when the graphical visualizations might have issues
        try:
            if 'plant_name' in df.columns and 'inverter_name' in df.columns:
                # Create a plant and inverter summary
                plt.figure(figsize=(14, 8))
                plt.axis('off')
                
                # Get unique plants and their inverters
                plant_inverters = {}
                inverter_energy = {}
                
                # Use display-friendly versions if available
                plant_col = 'plant_name_display' if 'plant_name_display' in df.columns else 'plant_name'
                inverter_col = 'inverter_name_display' if 'inverter_name_display' in df.columns else 'inverter_name'
                
                # Enhance data validation to ensure all values are properly converted
                df[plant_col] = df[plant_col].fillna('Unknown Plant').astype(str)
                df[inverter_col] = df[inverter_col].fillna('Unknown Inverter').astype(str)
                
                # Add try/except to better handle datatype issues
                try:
                    # Group inverters by plant and get their energy
                    for _, row in df.drop_duplicates(['inverter_serial']).iterrows():
                        plant = str(row[plant_col])
                        inverter = str(row[inverter_col])
                        
                        if plant not in plant_inverters:
                            plant_inverters[plant] = []
                        
                        plant_inverters[plant].append(inverter)
                        
                        # Get total energy for this inverter
                        inverter_data = df[df['inverter_serial'] == row['inverter_serial']]
                        total_energy = inverter_data['energy_today'].sum()
                        inverter_energy[inverter] = total_energy
                except Exception as e:
                    logger.error(f"Error while processing plant/inverter data: {e}")
                    # Create minimal placeholder data
                    plant_inverters = {"Unknown Plant": ["Unknown Inverter"]}
                    inverter_energy = {"Unknown Inverter": 0.0}
                
                # Create a text table
                table_text = []
                table_text.append("Plant and Inverter Summary:")
                table_text.append("-" * 80)
                table_text.append(f"{'Plant':<40} {'Inverters':<20} {'Energy (kWh)':<20}")
                table_text.append("-" * 80)
                
                for plant, inverters in sorted(plant_inverters.items()):
                    plant_energy = sum(inverter_energy.get(inv, 0) for inv in inverters)
                    inv_count = len(inverters)
                    table_text.append(f"{str(plant)[:38]:<40} {inv_count:<20} {plant_energy:.2f}")
                    
                    # List inverters under this plant
                    for inverter in sorted(inverters):
                        energy = inverter_energy.get(inverter, 0)
                        table_text.append(f"  ├─ {str(inverter)[:36]:<38} {'':<20} {energy:.2f}")
                
                # Add the table to the figure
                plt.text(0.05, 0.95, "\n".join(table_text), fontfamily='monospace', 
                         verticalalignment='top', horizontalalignment='left',
                         transform=plt.gca().transAxes, fontsize=9)
                
                plt.title('Plant and Inverter Summary', fontsize=16, pad=20)
                plt.tight_layout()
                summary_file = os.path.join(output_dir, 'plant_inverter_summary.png')
                plt.savefig(summary_file, dpi=120)
                plt.close()
                plot_files.append(summary_file)
        except Exception as e:
            logger.error(f"Error generating plant and inverter summary: {e}")
            # Don't let this error stop the rest of the report
        
        logger.info(f"Generated {len(plot_files)} enhanced inverter performance plots")
        return plot_files
        
    except Exception as e:
        logger.error(f"Error generating inverter performance plots: {e}")
        logger.error(traceback.format_exc())
        return plot_files
