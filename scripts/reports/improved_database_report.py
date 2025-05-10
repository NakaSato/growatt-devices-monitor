#!/usr/bin/env python3
"""
Improved Database Report Generator

Generate PDF reports with data visualizations from the database.
This script uses the new PDF utilities module for better styling and layout.

Usage:
    python improved_database_report.py [--days DAYS] [--email EMAIL] [--output OUTPUT]
"""

import os
import sys
import logging
import argparse
import tempfile
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib

# Import script utilities
from script import configure_script_logging
from script.reports.pdf_utils import PDFReport
from script.utils import create_common_parser, add_date_range_args, parse_date_range

# Configure logging
logger = configure_script_logging("improved_database_report")

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
                e.id,
                e.device_sn as serial_number,
                e.energy_today,
                e.energy_total,
                e.ac_power,
                e.dc_power,
                e.today_income,
                e.total_income,
                e.currency,
                e.date,
                e.last_update,
                d.alias,
                d.type,
                p.name as plant_name
            FROM 
                energy_stats e
            LEFT JOIN 
                devices d ON e.device_sn = d.serial_number
            LEFT JOIN 
                plants p ON d.plant_id = p.id
            WHERE 
                e.date BETWEEN %s AND %s
            ORDER BY 
                e.device_sn, e.date
        """
        
        # Execute the query
        results = db.query(query, (start_date_str, end_date_str))
        
        if not results:
            logger.warning(f"No energy data found for the period {start_date_str} to {end_date_str}")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Parse dates
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        if 'last_update' in df.columns:
            df['last_update'] = pd.to_datetime(df['last_update'])
        
        logger.info(f"Fetched {len(df)} energy records for {len(df['serial_number'].unique()) if 'serial_number' in df.columns else 0} devices")
        return df
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching energy data: {e}")
        return pd.DataFrame()

def generate_device_status_plots(df: pd.DataFrame) -> List[plt.Figure]:
    """
    Generate device status plots
    
    Args:
        df: DataFrame containing device status data
        
    Returns:
        List[plt.Figure]: List of matplotlib figure objects
    """
    if df.empty:
        logger.warning("No device status data to plot")
        return []
        
    figures = []
    
    try:
        # Create a temporary directory for plots
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Overall status distribution by device type
            fig, ax = plt.subplots(figsize=(10, 7))
            
            # Get current status for each device
            current_status = df.sort_values('last_update_time').groupby('serial_number').last()
            
            # Count statuses by device type
            status_by_type = pd.crosstab(
                current_status['type'], 
                current_status['status'].apply(lambda x: 'Online' if x in ['1', 'online', 'Online'] else 'Offline')
            )
            
            # Plot stacked bar chart
            status_by_type.plot(kind='bar', stacked=True, ax=ax, colormap='viridis')
            
            ax.set_title('Device Status by Type', fontsize=14)
            ax.set_xlabel('Device Type', fontsize=12)
            ax.set_ylabel('Count', fontsize=12)
            plt.legend(title='Status')
            plt.tight_layout()
            
            figures.append(fig)
            
            # 2. Status timeline for each device (limit to 10 for readability)
            # Get devices with most status changes
            status_changes = df.groupby('serial_number').size().sort_values(ascending=False)
            top_devices = status_changes.head(10).index.tolist()
            
            if top_devices:
                fig, ax = plt.subplots(figsize=(12, 8))
                
                for i, device in enumerate(top_devices):
                    device_data = df[df['serial_number'] == device]
                    
                    # Get device alias or use serial number
                    alias = device_data['alias'].iloc[0] if not device_data['alias'].iloc[0] in [None, '', 'null'] else device
                    
                    # Plot status over time (use a small y-offset for each device to separate them)
                    ax.scatter(
                        device_data['last_update_time'],
                        device_data['status_value'] + (i * 0.1),  # Small offset for each device
                        label=alias,
                        alpha=0.7
                    )
                
                ax.set_title('Device Status Timeline (Top 10 Devices with Most Changes)', fontsize=14)
                ax.set_xlabel('Time', fontsize=12)
                ax.set_ylabel('Status (-1=Offline, 1=Online)', fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # Set y-ticks to show status values
                ax.set_yticks([-1, 0, 1])
                ax.set_yticklabels(['Offline', 'Unknown', 'Online'])
                
                # Add legend outside the plot
                ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                
                plt.tight_layout()
                figures.append(fig)
            
            # 3. Uptime percentage by plant
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Calculate uptime (percentage of status=1 readings)
            uptime = df.groupby(['plant_name', 'serial_number']).apply(
                lambda x: (x['status_value'] == 1).sum() / len(x) * 100 if len(x) > 0 else 0
            ).reset_index()
            uptime.columns = ['plant_name', 'serial_number', 'uptime_percentage']
            
            # Group by plant and calculate average uptime
            plant_uptime = uptime.groupby('plant_name')['uptime_percentage'].mean().reset_index()
            plant_uptime = plant_uptime.sort_values('uptime_percentage', ascending=False)
            
            # Create horizontal bar chart
            sns.barplot(x='uptime_percentage', y='plant_name', data=plant_uptime, ax=ax, palette='viridis')
            
            ax.set_title('Average Device Uptime by Plant (%)', fontsize=14)
            ax.set_xlabel('Uptime Percentage', fontsize=12)
            ax.set_ylabel('Plant', fontsize=12)
            ax.grid(True, axis='x', alpha=0.3)
            
            # Add percentage labels
            for i, v in enumerate(plant_uptime['uptime_percentage']):
                ax.text(v + 1, i, f"{v:.1f}%", va='center')
            
            plt.tight_layout()
            figures.append(fig)
            
        return figures
        
    except Exception as e:
        logger.error(f"Error generating device status plots: {e}")
        return figures

def generate_energy_plots(df: pd.DataFrame) -> List[plt.Figure]:
    """
    Generate plots from energy data
    
    Args:
        df: DataFrame containing energy data
        
    Returns:
        List[plt.Figure]: List of matplotlib figure objects
    """
    if df.empty:
        logger.warning("No energy data to plot")
        return []
    
    figures = []
    
    try:
        # 1. Daily energy production by day
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Group by date and sum energy
        daily_energy = df.groupby('date')['energy_today'].sum().reset_index()
        daily_energy = daily_energy.sort_values('date')
        
        # Plot bar chart
        sns.barplot(x='date', y='energy_today', data=daily_energy, ax=ax, palette='viridis')
        
        ax.set_title('Daily Energy Production', fontsize=14)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Energy (kWh)', fontsize=12)
        
        # Format x-axis date labels
        plt.xticks(rotation=45)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        
        plt.tight_layout()
        figures.append(fig)
        
        # 2. Energy production by device
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Calculate total energy by device
        device_energy = df.groupby(['serial_number', 'alias'])['energy_today'].sum().reset_index()
        device_energy = device_energy.sort_values('energy_today', ascending=False)
        
        # Limit to top 15 devices for readability
        device_energy = device_energy.head(15)
        
        # Use alias if available, otherwise use serial number
        device_energy['display_name'] = device_energy.apply(
            lambda x: x['alias'] if x['alias'] and x['alias'] not in ['null', ''] else x['serial_number'], 
            axis=1
        )
        
        # Plot horizontal bar chart
        sns.barplot(y='display_name', x='energy_today', data=device_energy, ax=ax, palette='viridis')
        
        ax.set_title('Total Energy Production by Device (Top 15)', fontsize=14)
        ax.set_xlabel('Energy (kWh)', fontsize=12)
        ax.set_ylabel('Device', fontsize=12)
        
        plt.tight_layout()
        figures.append(fig)
        
        # 3. Energy production by plant
        if 'plant_name' in df.columns:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Calculate total energy by plant
            plant_energy = df.groupby('plant_name')['energy_today'].sum().reset_index()
            plant_energy = plant_energy.sort_values('energy_today', ascending=False)
            
            # Plot bar chart
            sns.barplot(y='plant_name', x='energy_today', data=plant_energy, ax=ax, palette='viridis')
            
            ax.set_title('Total Energy Production by Plant', fontsize=14)
            ax.set_xlabel('Energy (kWh)', fontsize=12)
            ax.set_ylabel('Plant', fontsize=12)
            
            plt.tight_layout()
            figures.append(fig)
        
        # 4. AC Power trends (averaged across devices)
        if 'ac_power' in df.columns and 'date' in df.columns and len(df['date'].unique()) > 1:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Group by date and calculate average AC power
            ac_power_trend = df.groupby('date')['ac_power'].mean().reset_index()
            ac_power_trend = ac_power_trend.sort_values('date')
            
            # Plot line chart
            sns.lineplot(x='date', y='ac_power', data=ac_power_trend, ax=ax, marker='o')
            
            ax.set_title('Average AC Power Over Time', fontsize=14)
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('AC Power (W)', fontsize=12)
            
            # Format x-axis date labels
            plt.xticks(rotation=45)
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
            
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            figures.append(fig)
        
        return figures
        
    except Exception as e:
        logger.error(f"Error generating energy plots: {e}")
        return figures

def create_pdf_report(
    status_df: pd.DataFrame, 
    energy_df: pd.DataFrame, 
    status_plots: List[plt.Figure], 
    energy_plots: List[plt.Figure],
    days: int,
    output_file: str = None
) -> str:
    """
    Create a PDF report with device status and energy data
    
    Args:
        status_df: DataFrame with device status data
        energy_df: DataFrame with energy data
        status_plots: List of status plot figures
        energy_plots: List of energy plot figures
        days: Number of days the report covers
        output_file: Optional output file path
        
    Returns:
        str: Path to the generated PDF file
    """
    # Create output directory if it doesn't exist
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename with timestamp if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(reports_dir, f"growatt_report_{timestamp}.pdf")
    
    try:
        # Create PDF report
        report = PDFReport(
            filename=output_file,
            title="Growatt Devices Performance Report"
        )
        
        # Add title page with metadata
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        metadata = {
            "Report Period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "Total Devices": str(len(status_df['serial_number'].unique())) if not status_df.empty else "0",
            "Plants": str(len(status_df['plant_name'].unique())) if not status_df.empty else "0"
        }
        
        if not energy_df.empty:
            metadata["Total Energy Production"] = f"{energy_df['energy_today'].sum():.2f} kWh"
        
        report.add_title_page(
            subtitle=f"Data for the Last {days} Days",
            metadata=metadata
        )
        
        # Device Status Section
        report.add_heading("Device Status Analysis")
        
        if not status_df.empty:
            # Add summary statistics
            online_devices = status_df[status_df['status_value'] == 1]['serial_number'].nunique()
            offline_devices = status_df[status_df['status_value'] == -1]['serial_number'].nunique()
            
            status_summary = (
                f"During this period, {len(status_df['serial_number'].unique())} devices were monitored. "
                f"{online_devices} devices reported online status and {offline_devices} devices reported offline status at some point."
            )
            
            report.add_paragraph(status_summary)
            
            # Add status plots
            for fig in status_plots:
                report.add_plot(fig=fig)
                
            # Add current device status table
            report.add_heading("Current Device Status", level=2)
            
            # Get current status for each device
            current_status = status_df.sort_values('last_update_time').groupby('serial_number').last()
            current_status = current_status.reset_index()[['serial_number', 'alias', 'status', 'last_update_time', 'plant_name']]
            
            # Format for display
            current_status['last_update_time'] = current_status['last_update_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Add to report
            report.add_dataframe(current_status, max_rows=15)
            
        else:
            report.add_paragraph("No device status data available for this period.")
        
        # Energy Production Section
        report.add_page_break()
        report.add_heading("Energy Production Analysis")
        
        if not energy_df.empty:
            # Add summary statistics
            total_energy = energy_df['energy_today'].sum()
            avg_daily_energy = energy_df.groupby('date')['energy_today'].sum().mean()
            
            energy_summary = (
                f"During this period, a total of {total_energy:.2f} kWh of energy was produced, "
                f"with an average daily production of {avg_daily_energy:.2f} kWh."
            )
            
            report.add_paragraph(energy_summary)
            
            # Add energy plots
            for fig in energy_plots:
                report.add_plot(fig=fig)
                
            # Add energy production table by device
            report.add_heading("Energy Production by Device", level=2)
            
            # Calculate energy production by device
            device_energy = energy_df.groupby(['serial_number', 'alias', 'plant_name'])['energy_today'].sum().reset_index()
            device_energy = device_energy.sort_values('energy_today', ascending=False)
            
            # Format for display
            device_energy.columns = ['Serial Number', 'Device Name', 'Plant', 'Energy (kWh)']
            device_energy['Energy (kWh)'] = device_energy['Energy (kWh)'].round(2)
            
            # Add to report
            report.add_dataframe(device_energy, max_rows=15)
            
        else:
            report.add_paragraph("No energy production data available for this period.")
        
        # Build the report
        pdf_path = report.build()
        
        if pdf_path:
            logger.info(f"PDF report saved to {pdf_path}")
            return pdf_path
        else:
            logger.error("Failed to generate PDF report")
            return None
            
    except Exception as e:
        logger.error(f"Error creating PDF report: {e}")
        return None

def send_email(pdf_path: str, recipient: str) -> bool:
    """
    Send the PDF report via email
    
    Args:
        pdf_path: Path to the PDF report
        recipient: Email address to send the report to
        
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
        
        # Get email configuration
        smtp_server = Config.SMTP_SERVER
        smtp_port = Config.SMTP_PORT
        smtp_user = Config.SMTP_USERNAME
        smtp_password = Config.SMTP_PASSWORD
        smtp_use_tls = Config.SMTP_USE_TLS
        sender_email = Config.SENDER_EMAIL or smtp_user
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = f"Growatt Devices Performance Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = """
        Please find attached the Growatt Devices Performance Report.
        
        This report contains device status and energy production data for the monitored period.
        
        Regards,
        Growatt Devices Monitor
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        with open(pdf_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='pdf')
            attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(attachment)
        
        # Connect to SMTP server
        if smtp_use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            
        # Login and send email
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent successfully to {recipient}")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False

def main():
    """Main function"""
    # Create parser with common arguments
    parser = create_common_parser()
    parser.description = "Generate PDF reports with data from the database"
    
    # Add report-specific arguments
    add_date_range_args(parser)
    parser.add_argument("--email", dest="email", help="Email address to send the report to")
    parser.add_argument("--output", dest="output_file", help="Output file path for the PDF report")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Parse date range (default to 7 days)
    date_range = parse_date_range(args)
    days = date_range.get('days_back', 7)
    
    logger.info(f"Generating report for the last {days} days")
    
    # Fetch data
    status_df = fetch_device_status_data(days)
    energy_df = fetch_energy_data(days)
    
    # Check if we have data
    if status_df.empty and energy_df.empty:
        logger.error("No data available for the specified period")
        return 1
    
    # Generate plots
    status_plots = generate_device_status_plots(status_df)
    energy_plots = generate_energy_plots(energy_df)
    
    # Create PDF report
    pdf_path = create_pdf_report(
        status_df=status_df,
        energy_df=energy_df,
        status_plots=status_plots,
        energy_plots=energy_plots,
        days=days,
        output_file=args.output_file
    )
    
    if not pdf_path:
        logger.error("Failed to create PDF report")
        return 1
    
    # Send email if requested
    if args.email:
        if send_email(pdf_path, args.email):
            logger.info(f"Report emailed to {args.email}")
        else:
            logger.error(f"Failed to email report to {args.email}")
    
    logger.info(f"Report generation complete: {pdf_path}")
    print(f"Report saved to: {pdf_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 