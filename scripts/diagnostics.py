#!/usr/bin/env python3
"""
Diagnostic script for the Growatt Devices Monitor application.

This script checks for common issues that might prevent the application from
running correctly, such as missing configuration, database connectivity, etc.

Usage:
    python diagnostics.py
"""

import os
import sys
import logging
import importlib
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("diagnostics")

# Add parent directory to path to allow importing app modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

def check_system_info():
    """Print system information"""
    import platform
    
    logger.info("=== System Information ===")
    logger.info(f"Python Version: {platform.python_version()}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Current Directory: {os.getcwd()}")
    logger.info(f"Script Directory: {script_dir}")
    logger.info(f"Project Root: {project_root}")
    logger.info(f"Python Path: {sys.path}")

def check_required_packages():
    """Check if all required packages are installed"""
    logger.info("\n=== Required Packages ===")
    required_packages = [
        "pandas", "numpy", "matplotlib", "seaborn", 
        "psycopg2", "requests", "pymysql", "sqlalchemy"
    ]
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            logger.info(f"✅ {package}: Installed")
        except ImportError:
            logger.error(f"❌ {package}: Not installed")

def check_app_modules():
    """Check if app modules can be imported"""
    logger.info("\n=== Application Modules ===")
    
    modules = [
        ("app.config", "Config"),
        ("app.database", "DatabaseConnector")
    ]
    
    for module_path, class_name in modules:
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, class_name):
                logger.info(f"✅ {module_path}.{class_name}: Found")
            else:
                logger.error(f"❌ {module_path}.{class_name}: Class not found in module")
        except ImportError as e:
            logger.error(f"❌ {module_path}: Import error - {e}")
        except Exception as e:
            logger.error(f"❌ {module_path}: Error - {e}")

def check_database_connection():
    """Check database connection"""
    logger.info("\n=== Database Connection ===")
    
    try:
        from app.database import DatabaseConnector
        
        db = DatabaseConnector()
        # Try a simple query
        result = db.query("SELECT 1")
        if result:
            logger.info("✅ Database connection: Successful")
            # Debug the query result structure
            logger.info(f"Query result type: {type(result)}")
            logger.info(f"Query result sample: {str(result)[:100]}..." if result else "Empty result")
        else:
            logger.warning("⚠️ Database connection returned empty result")
            
        # Try to get table info
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """
        try:
            tables = db.query(tables_query)
            
            # Handle different result formats
            table_names = []
            if tables:
                logger.info(f"Tables result type: {type(tables)}")
                # Handle results as list of tuples or list of dictionaries
                if isinstance(tables, list):
                    if tables and isinstance(tables[0], tuple):
                        table_names = [t[0] if len(t) > 0 else None for t in tables]
                    elif tables and isinstance(tables[0], dict) and 'table_name' in tables[0]:
                        table_names = [t.get('table_name') for t in tables]
                    else:
                        # Try to extract in a generic way
                        logger.info(f"Unexpected tables result format: {str(tables[0])[:100]}")
                        try:
                            # Try to access first element of each result
                            table_names = [t[0] if hasattr(t, '__getitem__') else str(t) for t in tables]
                        except Exception as e:
                            logger.warning(f"Could not extract table names: {e}")
                            # Show the raw result for debugging
                            logger.info(f"Raw tables result: {tables}")
                elif isinstance(tables, dict):
                    # Some DB connectors might return results as a dict
                    if 'table_name' in tables:
                        table_names = [tables['table_name']]
                    else:
                        logger.warning(f"Unexpected dict format: {tables.keys()}")
                
                # Filter out None values
                table_names = [t for t in table_names if t is not None]
                
            if table_names:
                logger.info(f"Available tables: {', '.join(table_names)}")
                
                # Check for our expected tables
                expected_tables = ['devices', 'inverter_details', 'plants']
                for table in expected_tables:
                    if table in table_names:
                        logger.info(f"✅ Table '{table}': Found")
                        
                        # Check table schema for better diagnostics
                        columns_query = f"""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = '{table}'
                        """
                        try:
                            columns = db.query(columns_query)
                            column_info = []
                            
                            # Handle different result formats for column data
                            if columns and isinstance(columns, list):
                                if isinstance(columns[0], tuple) and len(columns[0]) >= 2:
                                    # Tuple format: [(name, type), ...]
                                    column_info = [(col[0], col[1]) for col in columns]
                                elif isinstance(columns[0], dict) and 'column_name' in columns[0]:
                                    # Dict format: [{'column_name': name, 'data_type': type}, ...]
                                    column_info = [(col.get('column_name'), col.get('data_type')) for col in columns]
                                else:
                                    logger.warning(f"Unexpected column result format: {columns[0]}")
                            
                            if column_info:
                                logger.info(f"Table '{table}' columns:")
                                for col_name, col_type in column_info:
                                    logger.info(f"  - {col_name} ({col_type})")
                                    
                                # For inverter_details specifically, check for the serial_number column
                                if table == 'inverter_details':
                                    serial_columns = [col[0] for col in column_info if col[0] and 'serial' in col[0].lower()]
                                    if serial_columns:
                                        logger.info(f"✅ Found potential serial columns in inverter_details: {', '.join(serial_columns)}")
                                    else:
                                        logger.warning("⚠️ No serial number column found in inverter_details table")
                                        
                                    timestamp_columns = [col[0] for col in column_info if col[0] and ('time' in col[0].lower() or 'date' in col[0].lower())]
                                    if timestamp_columns:
                                        logger.info(f"✅ Found potential timestamp columns in inverter_details: {', '.join(timestamp_columns)}")
                                    else:
                                        logger.warning("⚠️ No timestamp column found in inverter_details table")
                            else:
                                logger.warning(f"Could not retrieve column information for '{table}'")
                        except Exception as e:
                            logger.warning(f"Could not retrieve columns for table '{table}': {e}")
                    else:
                        logger.warning(f"⚠️ Table '{table}': Not found")
                        
                # Try a test join query to check for potential ambiguous column issues
                if 'devices' in table_names and 'inverter_details' in table_names:
                    # This section continues as before but will be more careful with data formats
                    try:
                        devices_columns = db.query("""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name = 'devices'
                        """)
                        inverter_details_columns = db.query("""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name = 'inverter_details'
                        """)
                        
                        devices_col_names = [col[0] for col in devices_columns]
                        inverter_details_col_names = [col[0] for col in inverter_details_columns]
                        
                        # Check for column name overlaps
                        common_columns = set(devices_col_names).intersection(set(inverter_details_col_names))
                        if common_columns:
                            logger.warning(f"⚠️ Found common column names in 'devices' and 'inverter_details' tables: {', '.join(common_columns)}")
                            logger.warning("This could cause ambiguous column references in JOIN queries")
                            logger.warning("Solution: Use table aliases for these columns in your queries")
                        
                        # Identify the likely serial number columns in each table
                        devices_serial_col = next((col for col in devices_col_names if 'serial' in col.lower()), None)
                        inverter_serial_col = next((col for col in inverter_details_col_names if 'serial' in col.lower()), None)
                        
                        if devices_serial_col and inverter_serial_col:
                            logger.info(f"For JOIN queries, use: inverter_details.{inverter_serial_col} = devices.{devices_serial_col}")
                        
                        # Attempt a simple unambiguous join query
                        if devices_serial_col and inverter_serial_col:
                            test_join_query = f"""
                                SELECT inv.{inverter_serial_col}, dev.alias
                                FROM inverter_details inv
                                JOIN devices dev ON inv.{inverter_serial_col} = dev.{devices_serial_col}
                                LIMIT 1
                            """
                            try:
                                test_result = db.query(test_join_query)
                                logger.info("✅ Test JOIN query executed successfully")
                            except Exception as e:
                                logger.warning(f"⚠️ Test JOIN query failed: {e}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to test join query: {e}")
            else:
                logger.warning("No tables found in database")
        except Exception as e:
            logger.warning(f"Could not retrieve table list: {e}")
            logger.warning(traceback.format_exc())
            
    except ImportError:
        logger.error("❌ Database connection: Could not import DatabaseConnector")
    except Exception as e:
        logger.error(f"❌ Database connection: Failed - {e}")
        logger.error(traceback.format_exc())

def check_email_config():
    """Check email configuration"""
    logger.info("\n=== Email Configuration ===")
    
    try:
        from app.config import Config
        
        # Check for email configuration
        config_items = [
            ('EMAIL_NOTIFICATIONS_ENABLED', bool),
            ('SMTP_SERVER', str),
            ('SMTP_PORT', int),
            ('SMTP_USERNAME', str),
            ('SMTP_PASSWORD', str),
            ('EMAIL_FROM', str),
            ('EMAIL_TO', str)
        ]
        
        for item, expected_type in config_items:
            if hasattr(Config, item):
                value = getattr(Config, item)
                if item == 'SMTP_PASSWORD':
                    value = '****' if value else None
                
                if value is None:
                    logger.warning(f"⚠️ {item}: Not set")
                elif not isinstance(value, expected_type):
                    logger.warning(f"⚠️ {item}: Type mismatch (expected {expected_type.__name__}, got {type(value).__name__})")
                else:
                    logger.info(f"✅ {item}: {value}")
            else:
                logger.warning(f"⚠️ {item}: Not found in Config")
                
        # Test if email is enabled
        if hasattr(Config, 'EMAIL_NOTIFICATIONS_ENABLED'):
            if Config.EMAIL_NOTIFICATIONS_ENABLED:
                logger.info("Email notifications are enabled")
            else:
                logger.warning("Email notifications are disabled in configuration")
    except ImportError:
        logger.error("❌ Email configuration: Could not import Config")
    except Exception as e:
        logger.error(f"❌ Email configuration check failed: {e}")

def check_telegram_config():
    """Check Telegram configuration"""
    logger.info("\n=== Telegram Configuration ===")
    
    try:
        from app.config import Config
        
        # Check for Telegram configuration
        config_items = [
            ('TELEGRAM_ENABLED', bool),
            ('TELEGRAM_BOT_TOKEN', str),
            ('TELEGRAM_CHAT_ID', str)
        ]
        
        for item, expected_type in config_items:
            if hasattr(Config, item):
                value = getattr(Config, item)
                if item == 'TELEGRAM_BOT_TOKEN':
                    if value:
                        # Mask the token for security
                        masked_token = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
                        logger.info(f"✅ {item}: {masked_token}")
                    else:
                        logger.warning(f"⚠️ {item}: Not set")
                else:
                    logger.info(f"✅ {item}: {value}")
            else:
                logger.warning(f"⚠️ {item}: Not found in Config")
                
        # Test if Telegram is enabled
        if hasattr(Config, 'TELEGRAM_ENABLED'):
            if Config.TELEGRAM_ENABLED:
                logger.info("Telegram notifications are enabled")
            else:
                logger.warning("Telegram notifications are disabled in configuration")
    except ImportError:
        logger.error("❌ Telegram configuration: Could not import Config")
    except Exception as e:
        logger.error(f"❌ Telegram configuration check failed: {e}")

def main():
    """Run all diagnostic checks"""
    logger.info("Starting Growatt Devices Monitor diagnostics...\n")
    
    try:
        check_system_info()
        check_required_packages()
        check_app_modules()
        check_database_connection()
        check_email_config()
        check_telegram_config()
        
        logger.info("\nDiagnostic checks completed.")
        logger.info("If you found issues, please check your configuration and environment.")
        logger.info("For help, refer to the project documentation or report issues on GitHub.")
    except Exception as e:
        logger.error(f"Diagnostic checks failed: {e}")
        logger.error(traceback.format_exc())
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
