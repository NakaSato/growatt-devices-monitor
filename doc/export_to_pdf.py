#!/usr/bin/env python3
"""
Markdown to PDF Exporter for Growatt Devices Monitor Documentation

This script converts markdown documentation files to PDF format.
It adds consistent headers, footers, and styling to create professional-looking manuals.

"""

import os
import sys
import argparse
import markdown
import datetime
from pathlib import Path
from jinja2 import Template

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# HTML template for the PDF output
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        @page {
            margin: 1cm;
            @top-center {
                content: "Growatt Devices Monitor";
                font-weight: bold;
                color: #333;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
            }
            @bottom-right {
                content: "Generated: {{ date }}";
                font-size: 9pt;
                color: #666;
            }
        }
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 1cm;
        }
        h1, h2, h3, h4 {
            color: #0056b3;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        h1 {
            page-break-before: always;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.3em;
        }
        h1:first-of-type {
            page-break-before: avoid;
        }
        a {
            color: #0056b3;
            text-decoration: none;
        }
        pre, code {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 0.2em 0.4em;
            font-family: "Courier New", monospace;
            font-size: 0.85em;
        }
        pre {
            padding: 1em;
            overflow-x: auto;
            line-height: 1.45;
        }
        pre code {
            background-color: transparent;
            border: none;
            padding: 0;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        img {
            max-width: 100%;
            height: auto;
        }
        blockquote {
            border-left: 4px solid #ddd;
            padding-left: 1em;
            margin-left: 0;
            color: #666;
        }
        .cover-page {
            text-align: center;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .cover-page h1 {
            font-size: 2.5em;
            border: none;
        }
        .cover-page .subtitle {
            font-size: 1.5em;
            margin-bottom: 2em;
            color: #666;
        }
        .cover-page .date {
            margin-top: 3em;
            color: #666;
        }
        .cover-page .logo {
            margin-bottom: 2em;
            max-width: 200px;
        }
        .footer {
            text-align: center;
            color: #666;
            font-size: 0.8em;
            margin-top: 2em;
        }
    </style>
</head>
<body>
{% if cover_page %}
<div class="cover-page">
    <img class="logo" src="../app/static/images/Growatt-logo.png" alt="Growatt Logo">
    <h1>{{ title }}</h1>
    <div class="subtitle">Growatt Devices Monitor Documentation</div>
    <div class="date">{{ date }}</div>
</div>
{% endif %}

{{ content|safe }}

<div class="footer">
    &copy; {{ year }} Growatt Devices Monitor. All rights reserved.
</div>
</body>
</html>
"""

def md_to_pdf(md_file, output_dir, cover_page=True, verbose=False):
    """Convert a markdown file to PDF"""
    if not WEASYPRINT_AVAILABLE:
        print(f"Error: WeasyPrint not available. Skipping PDF generation for {md_file}")
        return False
    
    try:
        # Read markdown content
        with open(md_file, 'r') as f:
            md_content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'codehilite', 'tables', 'toc']
        )
        
        # Extract title from markdown
        title = "Growatt Documentation"
        for line in md_content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        # Create output PDF path
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(md_file))[0] + '.pdf')
        
        # Render HTML template
        template = Template(HTML_TEMPLATE)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.datetime.now().year
        
        html = template.render(
            title=title,
            content=html_content,
            date=today,
            year=current_year,
            cover_page=cover_page
        )
        
        # Convert HTML to PDF
        HTML(string=html).write_pdf(output_file)
        
        if verbose:
            print(f"Created PDF: {output_file}")
        
        return True
    except Exception as e:
        print(f"Error converting {md_file} to PDF: {e}")
        return False

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description='Convert markdown files to PDF')
    parser.add_argument('-o', '--output', default='./pdf', help='Output directory for PDF files')
    parser.add_argument('-s', '--single', help='Convert a single markdown file to PDF')
    parser.add_argument('-a', '--all', action='store_true', help='Convert all markdown files in the directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-n', '--no-cover', action='store_true', help='Skip cover page')
    
    args = parser.parse_args()
    
    # Check if WeasyPrint is available
    if not WEASYPRINT_AVAILABLE:
        print("Warning: WeasyPrint is not installed. Please install it to generate PDFs:")
        print("pip install weasyprint")
        print("\nOn macOS you might need additional dependencies:")
        print("brew install pango gdk-pixbuf libffi")
        return 1
    
    # Create output directory if it doesn't exist
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert single file
    if args.single:
        file_path = os.path.abspath(args.single)
        if not os.path.exists(file_path):
            print(f"Error: File not found - {file_path}")
            return 1
        
        success = md_to_pdf(file_path, output_dir, not args.no_cover, args.verbose)
        return 0 if success else 1
    
    # Convert all markdown files
    if args.all:
        successful = 0
        failed = 0
        
        # Get all markdown files in the current directory
        md_files = list(Path('.').glob('*.md'))
        
        if not md_files:
            print("No markdown files found in the current directory.")
            return 1
        
        print(f"Converting {len(md_files)} markdown files to PDF...")
        
        for md_file in md_files:
            if md_to_pdf(str(md_file), output_dir, not args.no_cover, args.verbose):
                successful += 1
            else:
                failed += 1
        
        print(f"\nSummary: {successful} files converted successfully, {failed} files failed.")
        print(f"PDFs saved to: {output_dir}")
        
        return 0 if failed == 0 else 1
    
    # If no specific action provided, show help
    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())