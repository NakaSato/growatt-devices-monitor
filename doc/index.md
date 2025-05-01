# Growatt Devices Monitor Documentation

This collection contains manuals and guides for setting up, configuring, and using the Growatt Devices Monitor system.

## Table of Contents

1. [Getting Started](./readme.md) - Basic setup and project overview
2. [Docker Setup Guide](./README-docker.md) - Docker configuration and deployment
3. [Nginx Configuration](./README-nginx.md) - Web server and reverse proxy setup
4. [Cron Jobs for Data Synchronization](./README_CRON.md) - Automated data collection
5. [SVG Maps Guide](./README-SVG-MAPS.md) - Interactive solar installation maps

## Exporting to PDF

These markdown files can be exported to PDF using various tools:

### Option 1: Using VS Code

1. Install the "Markdown PDF" extension in VS Code
2. Open any markdown file
3. Right-click and select "Markdown PDF: Export (pdf)"
4. Or press F1 and type "Markdown PDF: Export (pdf)"

### Option 2: Using pandoc

```bash
# Install pandoc and wkhtmltopdf
# macOS:
brew install pandoc
brew install wkhtmltopdf

# Linux:
sudo apt-get install pandoc wkhtmltopdf

# Export a single file to PDF
pandoc -s readme.md -o readme.pdf

# Export all manuals to PDF
for file in *.md; do
  pandoc -s "$file" -o "${file%.md}.pdf"
done
```

### Option 3: Using mdpdf

```bash
# Install mdpdf globally
npm install -g mdpdf

# Export a single file
mdpdf readme.md

# Export all manuals
for file in *.md; do
  mdpdf "$file"
done
```

## Batch Export Script

A script called `export_to_pdf.py` has been added to this folder to automate the export process.
