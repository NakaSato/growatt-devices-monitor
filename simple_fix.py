#!/usr/bin/env python3
"""
Quick fix for the database_report.py file to remove the Union type hint
"""
import os
import sys

file_path = "scripts/reports/database_report.py"

def fix_file():
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the function signature
    content = content.replace(
        "def send_email(pdf_path: str, recipient: Union[str, list]) -> bool:",
        "def send_email(pdf_path: str, recipient) -> bool:"
    )
    
    # Write the file back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")
    return True

if __name__ == "__main__":
    if fix_file():
        print("Running the database report...")
        os.system("python3 scripts/reports/database_report.py")
    else:
        print("Failed to fix the file")
        sys.exit(1)
