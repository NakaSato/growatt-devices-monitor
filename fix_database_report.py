#!/usr/bin/env python3
"""
This script updates the database_report.py file to fix the email sending issue
"""
import os
import re
import sys
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the path to the database_report.py file
file_path = "scripts/reports/database_report.py"

# Define the replacement function definition
old_function_signature = r"def send_email\(pdf_path: str, recipient: Union\[str, list\]\) -> bool:"
new_function_signature = "def send_email(pdf_path: str, recipient) -> bool:"

# Define the modified content for the beginning of the function
old_function_start = r"def send_email\(pdf_path: str, recipient.*?\).*?\n    \"\"\""
new_function_start = """def send_email(pdf_path: str, recipient) -> bool:
    """
    Send the PDF report via email
    
    Args:
        pdf_path: Path to the PDF report
        recipient: Email address or list of addresses to send the report to
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Convert recipient to string if it's a list
    if isinstance(recipient, list):
        recipient = recipient[0] if recipient else ""
    
    if not recipient:
        logger.error("No recipient email provided")
        return False
        
    """

def fix_database_report():
    """Fix the database_report.py file to handle list recipients."""
    try:
        # Create a backup of the original file
        backup_file = file_path + ".bak"
        shutil.copy2(file_path, backup_file)
        logger.info(f"Created backup of {file_path} as {backup_file}")
        
        # Read the original file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Try to fix the Union import issue
        if "Union" in content and "from typing import" in content and "Union" not in content.split("from typing import")[1].split("\n")[0]:
            # Add Union to the typing import
            content = re.sub(
                r"from typing import (.*?)\n",
                r"from typing import \1, Union\n",
                content,
                count=1
            )
            logger.info("Added Union to typing imports")
        
        # Replace the function signature if the previous fix didn't work
        if "def send_email(pdf_path: str, recipient: Union[str, list]) -> bool:" in content:
            content = content.replace(
                "def send_email(pdf_path: str, recipient: Union[str, list]) -> bool:",
                "def send_email(pdf_path: str, recipient) -> bool:"
            )
            logger.info("Replaced function signature to avoid Union type hint")
            
            # Add recipient type handling
            content = re.sub(
                r"def send_email\(pdf_path: str, recipient\) -> bool:\s+\"\"\".*?\"\"\"",
                """def send_email(pdf_path: str, recipient) -> bool:
    \"\"\"
    Send the PDF report via email
    
    Args:
        pdf_path: Path to the PDF report
        recipient: Email address or list of addresses to send the report to
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    \"\"\"
    # Convert recipient to string if it's a list
    if isinstance(recipient, list):
        recipient = recipient[0] if recipient else ""
    
    if not recipient:
        logger.error("No recipient email provided")
        return False""",
                content,
                flags=re.DOTALL
            )
            logger.info("Added recipient type handling code")
        
        # Write the updated content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Successfully updated {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        # Restore backup if it exists
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, file_path)
            logger.info(f"Restored {file_path} from backup")
        return False

def read_file_chunk(file_path, start_line=0, num_lines=20):
    """Read a chunk of a file for inspection."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        start = max(0, start_line)
        end = min(len(lines), start + num_lines)
        
        return ''.join(lines[start:end])
    except Exception as e:
        return f"Error reading file: {e}"

if __name__ == "__main__":
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File {file_path} does not exist")
        sys.exit(1)
    
    # Show the current function definition
    function_def_line = 0
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "def send_email" in line:
                function_def_line = i
                break
    
    print("Current function definition:")
    print(read_file_chunk(file_path, function_def_line, 15))
    
    # Fix the file
    if fix_database_report():
        print("\nFixed function definition:")
        print(read_file_chunk(file_path, function_def_line, 15))
        
        # Run the database report
        print("\nRunning database report...")
        os.system("python3 scripts/reports/database_report.py")
    else:
        logger.error("Failed to fix database_report.py")
        sys.exit(1)
