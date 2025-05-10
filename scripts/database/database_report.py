#!/usr/bin/env python3
"""
Script for generating database reports with data visualization and sending them via email.

This script queries the database for device statuses and energy production data,
generates visualizations, creates a PDF report, and sends it via email.

Usage:
    python database_report.py [--days DAYS] [--debug] [--email EMAIL]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
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

# Configure logging to write to file
LOG_FILE = "logs/database_report.log"
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

# Import Azure-specific components if running in Azure
AZURE_ENABLED = os.environ.get('AZURE_ENVIRONMENT', 'False').lower() in ('true', '1', 't')
azure_blob_storage = None

if AZURE_ENABLED:
    try:
        from app.azure_storage import azure_blob_storage
        from app.azure_monitoring import azure_monitoring
        logger.info("Azure integration enabled for database reports")
    except ImportError:
        logger.warning("Azure modules not available despite AZURE_ENVIRONMENT being True")

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

def fetch_device_status_data(days: int = 7) -> pd.DataFrame:
    """
    Fetch device status data from the database for the specified number of days
    
    Args:
        days: Number of days to look back
        
    Returns:
        pd.DataFrame: DataFrame containing device status data
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
        
        # Query for device status history
        query = """
            SELECT 
                d.serial_number, 
                d.alias, 
                d.status, 
                d.last_update_time,
                d.type,
                p.name as plant_name
            FROM 
                devices d
            LEFT JOIN 
                plants p ON d.plant_id = p.id
            WHERE 
                d.last_update_time BETWEEN %s AND %s
            ORDER BY 
                d.serial_number, d.last_update_time
        """
        
        # Execute the query using the DatabaseConnector
        results = db.query(query, (start_date_str, end_date_str))
        
        if not results:
            logger.warning(f"No device status data found for the period {start_date_str} to {end_date_str}")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Parse dates
        df['last_update_time'] = pd.to_datetime(df['last_update_time'])
        
        # Clean status values
        df['status_value'] = df['status'].apply(lambda x: 
                                            -1 if x == '-1' or x == 'offline' or x == 'Offline' else
                                            0 if x == '0' else
                                            1 if x == '1' or x == 'online' or x == 'Online' else
                                            float(x) if isinstance(x, str) and x.replace('.', '', 1).replace('-', '', 1).isdigit() else
                                            None)
        
        logger.info(f"Fetched {len(df)} device status records for {len(df['serial_number'].unique())} devices")
        return df
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching device status data: {e}")
        return pd.DataFrame()

def fetch_energy_data(days: int = 7) -> pd.DataFrame:
    """
    Fetch energy production data from the database
    
    Args:
        days: Number of days to look back
        
    Returns:
        pd.DataFrame: DataFrame containing energy production data
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
        
        # Query for energy data
        query = """
            SELECT 
                d.serial_number, 
                d.alias, 
                d.type,
                p.name as plant_name,
                de.energy_today,
                de.energy_total,
                de.ac_power,
                de.collected_at
            FROM 
                device_data de
            JOIN
                devices d ON de.device_serial_number = d.serial_number
            LEFT JOIN 
                plants p ON d.plant_id = p.id
            WHERE 
                de.collected_at BETWEEN %s AND %s
            ORDER BY 
                d.serial_number, de.collected_at
        """
        
        # Execute the query using the DatabaseConnector
        results = db.query(query, (start_date_str, end_date_str))
        
        if not results:
            logger.warning(f"No energy data found for the period {start_date_str} to {end_date_str}")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Parse dates
        df['collected_at'] = pd.to_datetime(df['collected_at'])
        
        # Convert energy columns to numeric
        for col in ['energy_today', 'energy_total', 'ac_power']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.info(f"Fetched {len(df)} energy records for {len(df['serial_number'].unique())} devices")
        return df
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching energy data: {e}")
        return pd.DataFrame()

def generate_device_status_plots(df: pd.DataFrame, output_dir: str) -> List[str]:
    """
    Generate plots from device status data
    
    Args:
        df: DataFrame containing device status data
        output_dir: Directory to save plots
        
    Returns:
        List[str]: List of generated plot file paths
    """
    if df.empty:
        logger.warning("No data available to generate device status plots")
        return []
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    plot_files = []
    
    try:
        # Set Seaborn style
        sns.set_style("whitegrid")
        
        # 1. Status Distribution Plot
        plt.figure(figsize=(10, 6))
        status_counts = df['status'].value_counts().sort_values(ascending=False)
        sns.barplot(x=status_counts.index, y=status_counts.values)
        plt.title('Device Status Distribution')
        plt.xlabel('Status')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        status_dist_file = os.path.join(output_dir, 'status_distribution.png')
        plt.savefig(status_dist_file)
        plt.close()
        plot_files.append(status_dist_file)
        
        # 2. Status by Device Type
        plt.figure(figsize=(12, 8))
        type_status = pd.crosstab(df['type'], df['status'])
        type_status.plot(kind='bar', stacked=True)
        plt.title('Device Status by Device Type')
        plt.xlabel('Device Type')
        plt.ylabel('Count')
        plt.legend(title='Status')
        plt.tight_layout()
        type_status_file = os.path.join(output_dir, 'status_by_type.png')
        plt.savefig(type_status_file)
        plt.close()
        plot_files.append(type_status_file)
        
        # 3. Status Timeline (for devices with multiple records)
        if len(df['last_update_time'].unique()) > 1:
            devices_with_changes = df.groupby('serial_number')['status_value'].nunique()
            devices_with_changes = devices_with_changes[devices_with_changes > 1].index.tolist()
            
            if devices_with_changes:
                # Choose up to 5 devices to show
                devices_to_plot = devices_with_changes[:5]
                
                plt.figure(figsize=(12, 8))
                for device in devices_to_plot:
                    device_df = df[df['serial_number'] == device]
                    device_name = device_df['alias'].iloc[0] if not device_df['alias'].isnull().all() else device
                    plt.plot(device_df['last_update_time'], device_df['status_value'], marker='o', linestyle='-', label=device_name)
                
                plt.title('Device Status Changes Over Time')
                plt.xlabel('Time')
                plt.ylabel('Status Value')
                plt.legend(title='Device', bbox_to_anchor=(1.05, 1), loc='upper left')
                plt.grid(True)
                plt.tight_layout()
                timeline_file = os.path.join(output_dir, 'status_timeline.png')
                plt.savefig(timeline_file)
                plt.close()
                plot_files.append(timeline_file)
        
        # 4. Offline Frequency by Plant
        plt.figure(figsize=(10, 6))
        offline_by_plant = df[df['status'].isin(['-1', 'offline', 'Offline'])].groupby('plant_name').size()
        
        if not offline_by_plant.empty:
            offline_by_plant = offline_by_plant.sort_values(ascending=False)
            sns.barplot(x=offline_by_plant.index, y=offline_by_plant.values)
            plt.title('Offline Events by Plant')
            plt.xlabel('Plant')
            plt.ylabel('Number of Offline Events')
            plt.xticks(rotation=45)
            plt.tight_layout()
            offline_plant_file = os.path.join(output_dir, 'offline_by_plant.png')
            plt.savefig(offline_plant_file)
            plt.close()
            plot_files.append(offline_plant_file)
        
        logger.info(f"Generated {len(plot_files)} device status plots")
        return plot_files
        
    except Exception as e:
        logger.error(f"Error generating device status plots: {e}")
        return plot_files

def generate_energy_plots(df: pd.DataFrame, output_dir: str) -> List[str]:
    """
    Generate plots from energy production data
    
    Args:
        df: DataFrame containing energy data
        output_dir: Directory to save plots
        
    Returns:
        List[str]: List of generated plot file paths
    """
    if df.empty:
        logger.warning("No data available to generate energy plots")
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
        daily_energy['date'] = daily_energy['collected_at'].dt.date
        daily_energy = daily_energy.groupby('date')['energy_today'].sum().reset_index()
        daily_energy['date'] = pd.to_datetime(daily_energy['date'])
        
        sns.lineplot(data=daily_energy, x='date', y='energy_today', marker='o')
        plt.title('Daily Energy Production')
        plt.xlabel('Date')
        plt.ylabel('Energy Today (kWh)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        daily_energy_file = os.path.join(output_dir, 'daily_energy.png')
        plt.savefig(daily_energy_file)
        plt.close()
        plot_files.append(daily_energy_file)
        
        # 2. Energy Production by Device
        plt.figure(figsize=(12, 8))
        
        # Group by device and sum energy_today
        device_energy = df.groupby('alias')['energy_today'].sum().sort_values(ascending=False)
        device_energy = device_energy.head(10)  # Top 10 devices
        
        sns.barplot(x=device_energy.index, y=device_energy.values)
        plt.title('Total Energy Production by Device (Top 10)')
        plt.xlabel('Device')
        plt.ylabel('Total Energy (kWh)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        device_energy_file = os.path.join(output_dir, 'device_energy.png')
        plt.savefig(device_energy_file)
        plt.close()
        plot_files.append(device_energy_file)
        
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
            plant_energy_file = os.path.join(output_dir, 'plant_energy.png')
            plt.savefig(plant_energy_file)
            plt.close()
            plot_files.append(plant_energy_file)
        
        # 4. AC Power Over Time (for top devices)
        plt.figure(figsize=(12, 8))
        
        # Get top 5 devices by total energy
        top_devices = df.groupby('alias')['energy_today'].sum().sort_values(ascending=False).head(5).index.tolist()
        
        # Filter data for top devices
        top_devices_df = df[df['alias'].isin(top_devices)]
        
        # Plot AC power over time for each top device
        for device in top_devices:
            device_df = top_devices_df[top_devices_df['alias'] == device]
            plt.plot(device_df['collected_at'], device_df['ac_power'], marker='.', linestyle='-', label=device)
        
        plt.title('AC Power Over Time (Top 5 Devices)')
        plt.xlabel('Time')
        plt.ylabel('AC Power (W)')
        plt.legend(title='Device', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        plt.tight_layout()
        ac_power_file = os.path.join(output_dir, 'ac_power_over_time.png')
        plt.savefig(ac_power_file)
        plt.close()
        plot_files.append(ac_power_file)
        
        logger.info(f"Generated {len(plot_files)} energy plots")
        return plot_files
        
    except Exception as e:
        logger.error(f"Error generating energy plots: {e}")
        return plot_files

def generate_pdf_report(
    status_df: pd.DataFrame, 
    energy_df: pd.DataFrame, 
    status_plots: List[str], 
    energy_plots: List[str],
    days: int
) -> str:
    """
    Generate a PDF report from the data and plots
    
    Args:
        status_df: DataFrame containing device status data
        energy_df: DataFrame containing energy data
        status_plots: List of device status plot file paths
        energy_plots: List of energy plot file paths
        days: Number of days the report covers
        
    Returns:
        str: Path to the generated PDF file
    """
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(reports_dir, f"device_report_{timestamp}.pdf")
    
    try:
        # Create PDF
        with PdfPages(pdf_path) as pdf:
            # Title page
            plt.figure(figsize=(12, 8))
            plt.axis('off')
            plt.text(0.5, 0.8, "Growatt Devices Status Report", fontsize=24, ha='center')
            plt.text(0.5, 0.7, f"Report Period: Last {days} Days", fontsize=18, ha='center')
            plt.text(0.5, 0.6, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=14, ha='center')
            
            # Device stats
            if not status_df.empty:
                total_devices = len(status_df['serial_number'].unique())
                offline_devices = len(status_df[status_df['status'].isin(['-1', 'offline', 'Offline'])]['serial_number'].unique())
                plt.text(0.5, 0.4, f"Total Devices: {total_devices}", fontsize=14, ha='center')
                plt.text(0.5, 0.35, f"Devices with Offline Events: {offline_devices}", fontsize=14, ha='center')
            
            # Energy stats
            if not energy_df.empty:
                total_energy = energy_df['energy_today'].sum()
                plt.text(0.5, 0.25, f"Total Energy Production: {total_energy:.2f} kWh", fontsize=14, ha='center')
            
            plt.tight_layout()
            pdf.savefig()
            plt.close()
            
            # Add device status plots
            for plot_file in status_plots:
                if os.path.exists(plot_file):
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    img = plt.imread(plot_file)
                    plt.imshow(img)
                    plt.tight_layout()
                    pdf.savefig()
                    plt.close()
            
            # Add energy plots
            for plot_file in energy_plots:
                if os.path.exists(plot_file):
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    img = plt.imread(plot_file)
                    plt.imshow(img)
                    plt.tight_layout()
                    pdf.savefig()
                    plt.close()
            
            # Add device status tables
            if not status_df.empty:
                # Get current status for each device
                current_status = status_df.sort_values('last_update_time').groupby('serial_number').last()
                current_status = current_status.reset_index()[['serial_number', 'alias', 'status', 'last_update_time', 'plant_name']]
                
                # Split into chunks for the table
                chunk_size = 20
                for i in range(0, len(current_status), chunk_size):
                    chunk = current_status.iloc[i:i+chunk_size]
                    
                    # Create a figure
                    plt.figure(figsize=(12, 8))
                    plt.axis('off')
                    plt.title('Current Device Status', fontsize=18)
                    
                    # Create the table
                    table = plt.table(
                        cellText=chunk.values,
                        colLabels=chunk.columns,
                        cellLoc='center',
                        loc='center',
                        bbox=[0.1, 0.1, 0.8, 0.8]
                    )
                    
                    # Style the table
                    table.auto_set_font_size(False)
                    table.set_fontsize(10)
                    table.scale(1, 1.5)
                    
                    pdf.savefig()
                    plt.close()
            
            # Add offline events summary if available
            if not status_df.empty:
                offline_events = status_df[status_df['status'].isin(['-1', 'offline', 'Offline'])]
                
                if not offline_events.empty:
                    offline_summary = offline_events.groupby('serial_number').agg({
                        'alias': 'first',
                        'plant_name': 'first',
                        'last_update_time': 'count'
                    }).rename(columns={'last_update_time': 'offline_count'}).reset_index()
                    
                    offline_summary = offline_summary.sort_values('offline_count', ascending=False)
                    
                    # Split into chunks for the table
                    chunk_size = 20
                    for i in range(0, len(offline_summary), chunk_size):
                        chunk = offline_summary.iloc[i:i+chunk_size]
                        
                        # Create a figure
                        plt.figure(figsize=(12, 8))
                        plt.axis('off')
                        plt.title('Offline Events Summary', fontsize=18)
                        
                        # Create the table
                        table = plt.table(
                            cellText=chunk.values,
                            colLabels=chunk.columns,
                            cellLoc='center',
                            loc='center',
                            bbox=[0.1, 0.1, 0.8, 0.8]
                        )
                        
                        # Style the table
                        table.auto_set_font_size(False)
                        table.set_fontsize(10)
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
        recipient: Email address(es) to send the report to (string or list of strings)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
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
            
        # Convert recipient to string if it's a list
        email_recipient = recipient[0] if isinstance(recipient, list) and recipient else recipient
        
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
        msg['To'] = email_recipient  # Use the processed recipient
        msg['Subject'] = f"Growatt Devices Status Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = """
        <html>
            <body>
                <h2>Growatt Devices Status Report</h2>
                <p>Please find attached the devices status report with data visualizations.</p>
                <p>This report includes device status information and energy production data.</p>
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
        
        # Connect to SMTP server and send email with detailed error handling
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
                
                logger.info(f"Sending email from {Config.EMAIL_FROM} to {email_recipient}")
                server.send_message(msg)
                logger.info("Email sent successfully")
            
            logger.info(f"Sent report email to {email_recipient}")
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

def main():
    """
    Main function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate database report with visualizations and send via email")
    parser.add_argument("--days", type=int, default=7, help="Number of days to include in the report")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--email", type=str, help="Email address to send report to (if not specified, uses the default from config)")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        
    try:
        logger.info("Starting database report generation")
        
        # Create temporary directory for plots
        temp_dir = os.path.join("reports", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Fetch data
        logger.info(f"Fetching device status data for the last {args.days} days")
        status_df = fetch_device_status_data(args.days)
        
        logger.info(f"Fetching energy data for the last {args.days} days")
        energy_df = fetch_energy_data(args.days)
        
        if status_df.empty and energy_df.empty:
            logger.error("No data available to generate report")
            return 1
            
        # Generate plots
        logger.info("Generating device status plots")
        status_plots = generate_device_status_plots(status_df, temp_dir)
        
        logger.info("Generating energy plots")
        energy_plots = generate_energy_plots(energy_df, temp_dir)
        
        # Generate PDF report
        logger.info("Generating PDF report")
        pdf_path = generate_pdf_report(status_df, energy_df, status_plots, energy_plots, args.days)
        
        if not pdf_path:
            logger.error("Failed to generate PDF report")
            return 1
            
        # Send email if requested
        if args.email:
            logger.info(f"Sending report to {args.email}")
            email_success = send_email(pdf_path, args.email)
            
            if not email_success:
                logger.error("Failed to send email")
                return 1
        else:
            # Try to get default email from config
            try:
                from app.config import Config
                if Config.EMAIL_TO:
                    logger.info(f"Sending report to default email: {Config.EMAIL_TO}")
                    email_success = send_email(pdf_path, Config.EMAIL_TO)
                    
                    if not email_success:
                        logger.error("Failed to send email to default address")
                        logger.info(f"Report generated at {pdf_path}")
                else:
                    logger.info(f"No email address specified and no default found. Report generated at {pdf_path}")
            except Exception:
                logger.info(f"Could not determine default email. Report generated at {pdf_path}")
        
        # Clean up temporary files
        for plot_file in status_plots + energy_plots:
            try:
                os.remove(plot_file)
            except Exception:
                pass
                
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
            
        logger.info("Database report generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in database report generation: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
