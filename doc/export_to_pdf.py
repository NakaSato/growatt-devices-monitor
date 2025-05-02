#!/usr/bin/env python3

import os
import sys
import glob
import markdown
import jinja2
from datetime import datetime
from weasyprint import HTML, CSS
import argparse
from pathlib import Path

# HTML template for the PDF output
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <!-- Import Thai fonts from Google Fonts -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&display=swap">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;500;600;700&display=swap">
    <style>
        @font-face {
            font-family: 'Sarabun';
            src: url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&display=swap');
            font-weight: normal;
            font-style: normal;
        }
        
        @font-face {
            font-family: 'Noto Sans Thai';
            src: url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;500;600;700&display=swap');
            font-weight: normal;
            font-style: normal;
        }
        
        /* Document properties and page setup */
        @page {
            margin: 2cm 2.5cm; /* Standard engineering report margins */
            @top-center {
                content: "{{ title }}";
                font-weight: 600;
                color: #333333;
                font-size: 9pt;
                font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
            }
            @bottom-left {
                content: "Growatt Devices Monitor System";
                font-size: 8pt;
                color: #4b5563;
                font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
            }
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8pt;
                color: #1f2937;
                font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
            }
            @bottom-center {
                content: "Generated: {{ date }}";
                font-size: 8pt;
                color: #4b5563;
                font-family: 'Sarabun', 'Noto Sans Thai', sans-serif;
            }
        }
        body {
            font-family: 'Sarabun', 'Noto Sans Thai', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.5; /* Increased from 1.4 for better readability */
            color: #1f2937;
            margin: 0;
            padding: 0;
            font-size: 11pt; /* Standard size for technical documents */
            text-align: justify;
            background-color: #ffffff;
            letter-spacing: 0.01em; /* Slightly increased letter spacing for improved legibility */
            word-spacing: 0.05em; /* Added word spacing for better text flow */
            counter-reset: section;
        }
        h1 {
            page-break-before: always;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 0.8em; /* Increased padding below heading */
            font-size: 20pt; /* Increased from 14pt for better hierarchy */
            color: #111827; /* Changed to dark gray/almost black color */
            font-weight: bold; /* Bold as specified in style guide */
            letter-spacing: 0.01em; /* Slight letter spacing for improved readability */
            word-spacing: 0.05em; /* Added word spacing for better flow */
            counter-reset: subsection;
            margin-bottom: 1em; /* Increased bottom margin for better spacing */
        }
        h1:first-of-type {
            page-break-before: avoid;
        }
        h1::before {
            counter-increment: section;
            content: counter(section) ". ";
        }
        h2 {
            font-size: 18pt;
            border-bottom: 1px solid #e5e7eb;
            color: #1f2937;
            counter-reset: subsubsection;
            padding-bottom: 0.5em; /* Added padding below h2 */
            margin-top: 1.8em; /* Increased top margin for better section separation */
            letter-spacing: 0.01em; /* Slight letter spacing */
        }
        h2::before {
            counter-increment: subsection;
            content: counter(section) "." counter(subsection) " ";
        }
        h3 {
            font-size: 16pt; /* Increased from 15pt */
            color: #374151;
            margin-top: 1.6em; /* Increased spacing before h3 */
            letter-spacing: 0.01em; /* Slight letter spacing */
        }
        h3::before {
            counter-increment: subsubsection;
            content: counter(section) "." counter(subsection) "." counter(subsubsection) " ";
        }
        h4 {
            font-size: 14pt; /* Increased from 13pt */
            color: #4b5563;
            margin-top: 1.4em; /* Increased spacing before h4 */
            letter-spacing: 0.01em; /* Slight letter spacing */
        }
        p {
            margin: 1em 0 1.4em 0;  /* Increased bottom margin for paragraphs */
            line-height: 1.8;  /* Better line height for paragraph text */
            text-align: justify;
            hyphens: auto;
            orphans: 3;
            widows: 3;
            letter-spacing: 0.01em; /* Slight letter spacing for better readability */
            word-spacing: 0.03em; /* Add word spacing for text flow */
        }
        a {
            color: #2563eb;
            text-decoration: none;
        }
        pre, code {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
            font-size: 10pt; /* Increased from 0.9em for better readability */
            letter-spacing: 0.01em; /* Slight letter spacing for code readability */
        }
        code {
            padding: 0.3em 0.5em;  /* Increased padding for inline code */
            white-space: nowrap;
            color: #166534;
        }
        pre {
            padding: 1.2em 1.4em;  /* Increased horizontal padding for code blocks */
            overflow-x: auto;
            line-height: 1.6;  /* Improved line height for code blocks */
            page-break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 1.5em 0;  /* Increased margins */
            position: relative;
            border-left: 4px solid #15803d;
        }
        pre code {
            background-color: transparent;
            border: none;
            padding: 0;
            white-space: pre;
            color: #1f2937;
        }
        /* Code language tag */
        pre::before {
            content: attr(data-language);
            position: absolute;
            top: 0;
            right: 0;
            color: #6b7280;
            font-size: 0.75em;
            padding: 0.3em 0.6em;
            background: #f9fafb;
            border-bottom-left-radius: 4px;
            border: 1px solid #e5e7eb;
            border-top: none;
            border-right: none;
        }
        ul, ol {
            margin: 1.2em 0 1.2em 1.8em;  /* Increased margins for lists */
            padding: 0;
            line-height: 1.7;  /* Improved line height for list items */
            letter-spacing: 0.01em; /* Slight letter spacing for readability */
        }
        li {
            margin-bottom: 0.7em;  /* Increased spacing between list items */
            padding-left: 0.3em;  /* Added left padding for list items */
        }
        li > ul, li > ol {
            margin-top: 0.5em; /* Increased spacing for nested lists */
            margin-bottom: 0.5em;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1.5em 0;
            border: 1px solid #e5e7eb;
            page-break-inside: avoid;
            font-size: 10.5pt; /* Increased from 0.95em for better readability */
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        th, td {
            border: 1px solid #e5e7eb;
            padding: 10px 12px;
            text-align: left;
        }
        th {
            background-color: #f3f4f6;
            font-weight: 600;
            color: #111827;
        }
        tr:nth-child(even) {
            background-color: #f9fafb;
        }
        img {
            max-width: 100%;
            height: auto;
            margin: 1em 0;
            page-break-inside: avoid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 6px;
        }
        blockquote {
            padding: 1em 1.5em;  /* Increased padding */
            margin: 1.5em 0;  /* Increased margins */
            background-color: #f0fdf4;
            color: #166534;
            font-style: italic;
            border-radius: 0 6px 6px 0;
            line-height: 1.7;  /* Better line height for quotes */
            border-left: 4px solid #15803d;
        }
        hr {
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 2em 0;
        }
        .cover-page {
            text-align: center;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            page-break-after: always;
            background: #ffffff;
            padding: 2em;
            position: relative;
            border: 1px solid #e5e7eb;
            margin: 2cm;
        }
        .cover-page h1 {
            font-size: 20pt;
            font-weight: bold;
            border: none;
            margin-bottom: 0.5em;
            color: #111827;
            letter-spacing: 0;
            line-height: 1.2;
            text-align: center;
        }
        .cover-page .subtitle {
            font-size: 14pt;
            margin-bottom: 3em;
            color: #374151;
            max-width: 80%;
            line-height: 1.4;
        }
        .cover-page .date {
            margin-top: 4em;
            color: #4b5563;
            font-size: 12pt;
        }
        .cover-page .version {
            margin-top: 1em;
            font-size: 10pt;
            color: #4b5563;
            font-weight: 500;
        }
        .cover-page .logo {
            margin-bottom: 3em;
            max-width: 180px;
        }
        .footer {
            text-align: center;
            color: #6b7280;
            font-size: 9pt;
            margin-top: 3em;
            border-top: 1px solid #e5e7eb;
            padding-top: 1em;
        }
        
        /* Technical documentation specific elements */
        .toc {
            background-color: #f9fafb;
            padding: 1.8em 2em;  /* Increased horizontal padding */
            margin: 2em 0;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            page-break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .toc h2 {
            margin-top: 0;
            font-size: 16pt;  /* Increased from 14pt */
            border: none;
            color: #15803d;
            margin-bottom: 1em;  /* Added bottom margin */
            letter-spacing: 0.01em;  /* Added slight letter spacing */
        }
        .toc ul {
            margin-left: 1.2em;  /* Increased left margin */
            margin-bottom: 0.8em;  /* Added bottom margin */
        }
        .toc li {
            margin-bottom: 0.5em;  /* Adjusted spacing between TOC items */
            line-height: 1.5;  /* Better line height for TOC items */
        }
        .toc a {
            color: #1f2937;
            text-decoration: none;
            letter-spacing: 0.01em;  /* Added letter spacing */
            word-spacing: 0.03em;  /* Added word spacing */
        }
        
        /* Technical diagram styles */
        .diagram {
            margin: 2em 0;
            padding: 1.5em;
            border: 1px solid #e5e7eb;
            background-color: #f9fafb;
            page-break-inside: avoid;
            border-radius: 6px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .diagram img {
            box-shadow: none;
            border: 1px solid #e5e7eb;
            max-width: 95%;
        }
        .diagram-caption {
            font-size: 0.9em;
            color: #4b5563;
            margin-top: 0.8em;
            font-style: italic;
        }
        
        /* Advanced callout boxes */
        .note, .warning, .tip, .important, .technical, .example {
            margin: 1.5em 0;
            padding: 1em 1em 1em 2.5em;
            border-left: 4px solid;
            background-color: #f9fafb;
            page-break-inside: avoid;
            border-radius: 0 6px 6px 0;
            position: relative;
            font-size: 0.95em;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .note::before, .warning::before, .tip::before, .important::before, .technical::before, .example::before {
            position: absolute;
            left: 0.8em;
            font-weight: bold;
        }
        .note {
            border-left-color: #2563eb;
            background-color: #eff6ff;
        }
        .note::before {
            content: "ℹ️";
            color: #2563eb;
        }
        .warning {
            border-left-color: #dc2626;
            background-color: #fef2f2;
        }
        .warning::before {
            content: "⚠️";
            color: #dc2626;
        }
        .tip {
            border-left-color: #15803d;
            background-color: #f0fdf4;
        }
        .tip::before {
            content: "💡";
            color: #15803d;
        }
        .important {
            border-left-color: #d97706;
            background-color: #fffbeb;
        }
        .important::before {
            content: "❗";
            color: #d97706;
        }
        .technical {
            border-left-color: #7c3aed;
            background-color: #f5f3ff;
        }
        .technical::before {
            content: "🔧";
            color: #7c3aed;
        }
        .example {
            border-left-color: #0891b2;
            background-color: #ecfeff;
        }
        .example::before {
            content: "📝";
            color: #0891b2;
        }
        
        /* API References */
        .api-section {
            margin: 2em 0;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            overflow: hidden;
            page-break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .api-header {
            background-color: #f3f4f6;
            padding: 1em;
            border-bottom: 1px solid #e5e7eb;
        }
        .api-header h3 {
            margin: 0;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 0.5em;
        }
        .api-header h3::before {
            content: "API";
            font-size: 0.7em;
            background-color: #15803d;
            color: white;
            padding: 0.3em 0.5em;
            border-radius: 4px;
            font-weight: 600;
            display: inline-block;
        }
        .api-content {
            padding: 1.2em;
        }
        .api-params {
            margin-top: 1em;
            background-color: #f9fafb;
            padding: 1em;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
        }
        .param-name {
            font-family: monospace;
            font-weight: bold;
            color: #111827;
            background-color: #f3f4f6;
            padding: 0.1em 0.3em;
            border-radius: 3px;
            border: 1px solid #e5e7eb;
        }
        .param-type {
            color: #6b7280;
            font-style: italic;
            font-size: 0.9em;
        }
        
        /* Code annotations */
        .code-annotation {
            display: block;
            color: #15803d;
            font-style: italic;
            margin-top: 0.3em;
            font-size: 0.9em;
            padding-left: 1.5em;
            border-left: 2px solid #15803d;
            line-height: 1.4;
        }
        
        /* Two-column layout for some sections */
        .two-column {
            display: flex;
            margin: 1.5em 0;
            page-break-inside: avoid;
            gap: 1.5em;
        }
        .column {
            flex: 1;
        }
        .column:first-child {
            border-right: 1px solid #e5e7eb;
            padding-right: 1.5em;
        }
        
        /* Command line output */
        .terminal {
            background-color: #1a1a1a;
            color: #f3f4f6;
            padding: 1.2em;
            border-radius: 6px;
            font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
            overflow-x: auto;
            margin: 1.5em 0;
            page-break-inside: avoid;
            line-height: 1.4;
            font-size: 0.9em;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .command {
            color: #22c55e;
            display: block;
            margin-bottom: 0.3em;
        }
        .output {
            color: #f3f4f6;
            display: block;
            margin-bottom: 0.8em;
        }
        
        /* Keyboard keys */
        kbd {
            background-color: #f3f4f6;
            border: 1px solid #d1d5db;
            border-bottom: 3px solid #d1d5db;
            border-radius: 3px;
            padding: 0.2em 0.5em;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 0.85em;
            box-shadow: 0 1px 1px rgba(0,0,0,0.1);
            display: inline-block;
            margin: 0 0.1em;
        }
        
        /* Version history */
        .version-history {
            width: 100%;
            margin: 2em 0;
            border-collapse: collapse;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .version-history th,
        .version-history td {
            padding: 0.8em 1em;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        .version-history th {
            background-color: #f3f4f6;
            font-weight: 600;
        }
        .version-number {
            font-family: monospace;
            color: #15803d;
            font-weight: 600;
        }
        
        /* Dark green box for key information */
        .key-info {
            background-color: #dcfce7;
            border: 1px solid #86efac;
            border-radius: 6px;
            padding: 1.2em;
            margin: 1.5em 0;
            position: relative;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .key-info::before {
            content: "KEY INFORMATION";
            position: absolute;
            top: -0.8em;
            left: 1em;
            background-color: #15803d;
            color: white;
            font-size: 0.7em;
            padding: 0.3em 0.6em;
            border-radius: 3px;
            font-weight: 600;
        }
        
        /* Page break control */
        .page-break {
            page-break-after: always;
        }
        .avoid-break {
            page-break-inside: avoid;
        }
        
        /* Document Metadata Section */
        .document-metadata {
            border: 1px solid #e5e7eb;
            background-color: #f8fafc;
            padding: 1.5em;
            margin: 2em 0;
            page-break-inside: avoid;
            font-size: 10pt;
        }
        .document-metadata h3 {
            margin-top: 0;
            font-size: 12pt;
            border-bottom: 1px solid #d1d5db;
            padding-bottom: 0.5em;
            color: #111827;
        }
        .metadata-table {
            width: 100%;
            margin: 1em 0 0 0;
            border-collapse: collapse;
        }
        .metadata-table td {
            padding: 0.5em;
            vertical-align: top;
            border: none;
        }
        .metadata-table tr td:first-child {
            font-weight: 600;
            width: 30%;
            color: #374151;
        }
        
        /* Table and Figure Captions */
        .figure {
            text-align: center;
            margin: 2em 0;
            page-break-inside: avoid;
        }
        .table-caption, .figure-caption {
            font-size: 10pt;
            color: #4b5563;
            margin-top: 0.5em;
            font-style: italic;
            text-align: center;
        }
        .table-caption {
            margin-bottom: 0.5em;
        }
        .figure-caption {
            margin-top: 0.8em;
        }
        
        /* References Section */
        .references {
            margin: 2em 0;
            padding: 1em;
            border: 1px solid #e5e7eb;
            background-color: #f9fafb;
        }
        .references h2 {
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0.5em;
            margin-top: 0;
        }
        .references ol {
            margin-left: 1.5em;
        }
        .reference-item {
            margin-bottom: 0.8em;
        }
    </style>
</head>
<body>
{% if cover_page %}
<div class="cover-page">
    {% if logo_path %}
    <img class="logo" src="{{ logo_path }}" alt="Growatt Logo">
    {% else %}
    <div style="font-size: 24pt; color: #15803d; font-weight: bold; margin-bottom: 2em;">Growatt Monitor</div>
    {% endif %}
    <h1>{{ title }}</h1>
    <div class="subtitle">Growatt Devices Monitoring System Documentation</div>
    <div class="date">{{ date }}</div>
    <div class="version">Version 1.0</div>
</div>
{% endif %}

{{ content|safe }}

<div class="footer">
    &copy; {{ year }} BORING9.DEV. All rights reserved.
</div>
</body>
</html>
"""

def convert_markdown_to_html(markdown_content):
    """Convert Markdown content to HTML."""
    # Use the Python-Markdown library to convert Markdown to HTML
    extensions = [
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.sane_lists',
    ]
    
    html_content = markdown.markdown(markdown_content, extensions=extensions)
    return html_content

def get_title_from_markdown(markdown_content):
    """Extract title from the first line of Markdown content."""
    lines = markdown_content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            return line[2:]  # Remove '# ' prefix
    return None  # Return None if no title found

def render_html_template(title, html_content, cover_page=True, logo_path=None):
    """Render HTML content with Jinja2 template."""
    template = jinja2.Template(HTML_TEMPLATE)
    today = datetime.now().strftime("%B %d, %Y")
    year = datetime.now().year
    
    # Verify logo path exists
    if logo_path and not os.path.exists(logo_path):
        print(f"⚠️ Warning: Logo file not found at {logo_path}")
        logo_path = None
    
    return template.render(
        title=title,
        content=html_content,
        date=today,
        year=year,
        cover_page=cover_page,
        logo_path=logo_path
    )

def create_pdf(html_content, output_path):
    """Convert HTML to PDF using WeasyPrint."""
    try:
        HTML(string=html_content).write_pdf(output_path)
        print(f"✅ Created PDF: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        return False

def process_markdown_file(markdown_path, output_dir, cover_page=True, logo_path=None):
    """Process a single Markdown file and convert it to PDF."""
    try:
        # Read Markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convert Markdown to HTML
        html_content = convert_markdown_to_html(markdown_content)
        
        # Get title from Markdown content
        title = get_title_from_markdown(markdown_content) or Path(markdown_path).stem
        
        # Render HTML template
        rendered_html = render_html_template(title, html_content, cover_page, logo_path)
        
        # Create output filename
        output_filename = os.path.basename(markdown_path).replace('.md', '.pdf')
        output_path = os.path.join(output_dir, output_filename)
        
        # Create PDF
        success = create_pdf(rendered_html, output_path)
        
        if success:
            print(f"✅ Successfully processed {markdown_path}")
            return True
        else:
            print(f"❌ Failed to create PDF for {markdown_path}")
            return False
    except Exception as e:
        print(f"❌ Error processing {markdown_path}: {e}")
        return False

def main():
    """Main function to convert all Markdown files to PDF."""
    parser = argparse.ArgumentParser(description='Convert Markdown files to PDF')
    parser.add_argument('--input', '-i', help='Input markdown file or directory', default='.')
    parser.add_argument('--output', '-o', help='Output PDF directory', default='pdf')
    parser.add_argument('--no-cover', help='Skip cover page', action='store_true')
    parser.add_argument('--font', help='Font family for Thai text (sarabun, noto, thsarabun)', default='sarabun')
    parser.add_argument('--logo', help='Path to logo image for cover page', default=None)
    args = parser.parse_args()
    
    # Determine base directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Handle input file or directory
    if os.path.isfile(args.input) and args.input.endswith('.md'):
        markdown_files = [args.input]
    elif os.path.isdir(args.input):
        markdown_files = glob.glob(os.path.join(args.input, '*.md'))
    else:
        print(f"❌ Invalid input: {args.input}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 Found {len(markdown_files)} Markdown files")
    
    # Process each Markdown file
    successful = 0
    for markdown_file in markdown_files:
        if process_markdown_file(markdown_file, output_dir, not args.no_cover, args.logo):
            successful += 1
    
    print(f"🎉 Successfully converted {successful} of {len(markdown_files)} files to PDF")
    print(f"📄 PDFs saved to: {output_dir}")

if __name__ == "__main__":
    main()
