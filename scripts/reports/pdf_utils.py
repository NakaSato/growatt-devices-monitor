#!/usr/bin/env python3
"""
PDF Generation Utilities

This module provides utilities for generating PDF reports with modern styling,
better layout, and reusable components.
"""

import os
import logging
import tempfile
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, ListFlowable, ListItem
)
import seaborn as sns
from pathlib import Path

# Import script utilities
from script import configure_script_logging

# Configure logging
logger = configure_script_logging("pdf_utils")

# Set up fonts for Thai text and general styling
def setup_fonts():
    """Set up fonts for the PDF reports, including Thai language support"""
    # First check for our own bundled font
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
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
                logger.warning(f"Failed to load font {font_path}: {str(e)}")

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
    
    # Set seaborn style for better looking plots
    sns.set_style("whitegrid")
    
    return registered_fonts

# Define color schemes
COLORS = {
    'primary': '#1a73e8',
    'secondary': '#34a853',
    'warning': '#fbbc04',
    'danger': '#ea4335',
    'info': '#4285f4',
    'light': '#f8f9fa',
    'dark': '#202124',
    'gray': '#5f6368',
    'background': '#ffffff',
    'text': '#202124',
    'grid': '#dadce0',
    'accent1': '#1a73e8',
    'accent2': '#34a853',
    'accent3': '#fbbc04',
    'accent4': '#ea4335',
    'accent5': '#4285f4',
}

class PDFReport:
    """Class for creating PDF reports with consistent styling"""
    
    def __init__(self, filename: str, title: str, pagesize=A4):
        """
        Initialize a PDF report
        
        Args:
            filename: Path where the PDF will be saved
            title: Title of the report
            pagesize: Page size (default: A4)
        """
        self.filename = filename
        self.title = title
        self.pagesize = pagesize
        self.story = []
        self.styles = self._create_styles()
        self.doc = SimpleDocTemplate(
            filename,
            pagesize=pagesize,
            leftMargin=1*cm,
            rightMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
            title=title
        )
        
        # Set up temp directory for images
        self.temp_dir = tempfile.mkdtemp()
        
        # Setup fonts
        setup_fonts()
        
    def _create_styles(self):
        """Create custom styles for the report"""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            leading=32,
            textColor=colors.HexColor(COLORS['primary']),
            spaceAfter=20
        ))
        
        # Heading 1 style
        styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor(COLORS['primary']),
            spaceAfter=10
        ))
        
        # Heading 2 style
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor(COLORS['dark']),
            spaceAfter=8
        ))
        
        # Normal text style
        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(COLORS['text'])
        ))
        
        # Info style (for metadata)
        styles.add(ParagraphStyle(
            name='Info',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            textColor=colors.HexColor(COLORS['gray'])
        ))
        
        return styles
    
    def add_title_page(self, subtitle: str = None, metadata: Dict[str, str] = None):
        """
        Add a title page to the report
        
        Args:
            subtitle: Optional subtitle
            metadata: Optional dictionary of metadata to display
        """
        self.story.append(Paragraph(self.title, self.styles['CustomTitle']))
        
        if subtitle:
            self.story.append(Paragraph(subtitle, self.styles['CustomHeading2']))
            
        self.story.append(Spacer(1, 0.5*inch))
        
        # Add metadata
        if metadata:
            for key, value in metadata.items():
                self.story.append(Paragraph(
                    f"<b>{key}:</b> {value}", 
                    self.styles['Info']
                ))
                
        self.story.append(Spacer(1, 0.25*inch))
        
        # Add generation timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.story.append(Paragraph(
            f"Generated on: {timestamp}", 
            self.styles['Info']
        ))
        
        self.story.append(PageBreak())
    
    def add_heading(self, text: str, level: int = 1):
        """
        Add a heading to the report
        
        Args:
            text: Heading text
            level: Heading level (1 or 2)
        """
        if level == 1:
            self.story.append(Paragraph(text, self.styles['CustomHeading1']))
        else:
            self.story.append(Paragraph(text, self.styles['CustomHeading2']))
        
        self.story.append(Spacer(1, 0.1*inch))
    
    def add_paragraph(self, text: str):
        """
        Add a paragraph to the report
        
        Args:
            text: Paragraph text
        """
        self.story.append(Paragraph(text, self.styles['CustomNormal']))
        self.story.append(Spacer(1, 0.1*inch))
    
    def add_spacer(self, height: float = 0.25):
        """
        Add vertical space to the report
        
        Args:
            height: Height in inches
        """
        self.story.append(Spacer(1, height*inch))
    
    def add_table(self, data: List[List], headers: List[str] = None, style: str = 'default'):
        """
        Add a table to the report
        
        Args:
            data: Table data as a list of rows
            headers: Optional list of column headers
            style: Table style ('default', 'striped', or 'colored')
        """
        if headers:
            table_data = [headers] + data
        else:
            table_data = data
            
        table = Table(table_data)
        
        # Define table style based on parameter
        if style == 'striped':
            style_commands = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['primary'])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(COLORS['grid'])),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]
            
            # Add striped rows
            for i in range(1, len(table_data), 2):
                style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor(COLORS['light'])))
                
        elif style == 'colored':
            style_commands = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['primary'])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(COLORS['grid'])),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]
            
            # Set different colors for columns
            colors_list = [COLORS['accent1'], COLORS['accent2'], COLORS['accent3'], 
                          COLORS['accent4'], COLORS['accent5']]
            
            for i, color in enumerate(colors_list):
                if i < len(table_data[0]):  # Don't exceed number of columns
                    for row in range(1, len(table_data)):
                        style_commands.append((
                            'TEXTCOLOR', (i, row), (i, row), 
                            colors.HexColor(color)
                        ))
        else:  # default style
            style_commands = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['primary'])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(COLORS['grid'])),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]
            
        table.setStyle(TableStyle(style_commands))
        self.story.append(table)
        self.story.append(Spacer(1, 0.2*inch))
    
    def add_plot(self, fig: Figure = None, plot_path: str = None, width: float = None, height: float = None):
        """
        Add a matplotlib plot to the report
        
        Args:
            fig: Matplotlib figure object
            plot_path: Path to a saved plot image
            width: Optional width in inches
            height: Optional height in inches
        """
        if fig is not None:
            # Save figure to temporary file
            plot_file = os.path.join(self.temp_dir, f"plot_{len(self.story)}.png")
            fig.savefig(plot_file, dpi=150, bbox_inches='tight')
            plot_path = plot_file
            
        if plot_path and os.path.exists(plot_path):
            img = Image(plot_path)
            
            # Set image dimensions if provided
            if width and height:
                img.drawWidth = width * inch
                img.drawHeight = height * inch
            elif width:
                img.drawWidth = width * inch
            elif height:
                img.drawHeight = height * inch
                
            self.story.append(img)
            self.story.append(Spacer(1, 0.2*inch))
    
    def add_page_break(self):
        """Add a page break to the report"""
        self.story.append(PageBreak())
    
    def add_dataframe(self, df: pd.DataFrame, title: str = None, max_rows: int = 20):
        """
        Add a pandas DataFrame to the report as a table
        
        Args:
            df: DataFrame to add
            title: Optional title for the table
            max_rows: Maximum number of rows to display (will create multiple tables if needed)
        """
        if df.empty:
            self.add_paragraph("No data available")
            return
            
        if title:
            self.add_heading(title, level=2)
            
        # Convert DataFrame to list of lists
        headers = df.columns.tolist()
        
        # Handle chunking for large DataFrames
        total_rows = len(df)
        chunks = [(i, min(i + max_rows, total_rows)) for i in range(0, total_rows, max_rows)]
        
        for i, (start, end) in enumerate(chunks):
            chunk = df.iloc[start:end]
            data = chunk.values.tolist()
            
            if len(chunks) > 1:
                chunk_title = f"{title} (Part {i+1}/{len(chunks)})" if title else f"Table (Part {i+1}/{len(chunks)})"
                self.add_heading(chunk_title, level=2)
                
            self.add_table(data, headers, style='striped')
            
            if i < len(chunks) - 1:
                self.add_page_break()
    
    def build(self):
        """Build and save the PDF report"""
        try:
            self.doc.build(self.story)
            logger.info(f"PDF report saved to {self.filename}")
            return self.filename
        except Exception as e:
            logger.error(f"Error building PDF report: {str(e)}")
            return None 