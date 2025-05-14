#!/usr/bin/env python3
"""
Database Visualizer for Growatt Devices Monitor

This script helps visualize data from the database for debugging purposes.
It provides insights into database structure, relationships between tables,
and sample data visualization to help understand the data before building reports.

Usage:
    python db_visualizer.py [--days DAYS] [--debug] [--output OUTPUT_DIR]
"""

import os
import sys
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_visualizer")

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

def visualize_table_structure(db, output_dir: str) -> None:
    """
    Visualize the structure of database tables
    
    Args:
        db: Database connector
        output_dir: Directory to save output files
    """
    try:
        # Get all tables in the database
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        tables = db.query(tables_query)
        
        if not tables:
            logger.warning("No tables found in database")
            return
            
        # Convert to list of strings
        if isinstance(tables[0], tuple):
            table_names = [t[0] for t in tables]
        elif isinstance(tables[0], dict) and 'table_name' in tables[0]:
            table_names = [t['table_name'] for t in tables]
        else:
            # Try to extract in a generic way
            table_names = []
            for t in tables:
                if hasattr(t, '__getitem__'):
                    try:
                        table_names.append(t[0])
                    except (IndexError, TypeError):
                        if hasattr(t, 'table_name'):
                            table_names.append(t.table_name)
                        else:
                            table_names.append(str(t))
                else:
                    table_names.append(str(t))
        
        # Create a dictionary to store table structures
        table_structures = {}
        
        for table in table_names:
            columns_query = f"""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """
            columns = db.query(columns_query)
            
            if not columns:
                logger.warning(f"No columns found for table {table}")
                continue
                
            # Process column information
            column_info = []
            for col in columns:
                if isinstance(col, tuple) and len(col) >= 3:
                    column_info.append({
                        'name': col[0],
                        'type': col[1],
                        'nullable': col[2]
                    })
                elif isinstance(col, dict):
                    column_info.append({
                        'name': col.get('column_name', 'unknown'),
                        'type': col.get('data_type', 'unknown'),
                        'nullable': col.get('is_nullable', 'unknown')
                    })
                else:
                    # Skip columns we can't process
                    continue
                    
            table_structures[table] = column_info
            
        # Generate a visualization of the table structure
        plt.figure(figsize=(14, len(table_structures) * 2))
        plt.axis('off')
        
        y_position = 0.98
        line_height = 0.04
        
        plt.text(0.5, y_position, "Database Structure", 
                fontsize=16, ha='center', fontweight='bold')
        y_position -= line_height * 2
        
        for table, columns in table_structures.items():
            plt.text(0.02, y_position, f"Table: {table}", 
                    fontsize=12, fontweight='bold')
            y_position -= line_height
            
            for col in columns:
                nullable = "NULL" if col['nullable'].lower() == 'yes' else "NOT NULL"
                plt.text(0.05, y_position, 
                        f"{col['name']} - {col['type']} {nullable}", 
                        fontsize=10)
                y_position -= line_height
                
            y_position -= line_height * 0.5
        
        # Save the image
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'database_structure.png'), dpi=120)
        plt.close()
        
        # Also save as text file for easier reference
        with open(os.path.join(output_dir, 'database_structure.txt'), 'w') as f:
            f.write("DATABASE STRUCTURE\n")
            f.write("=================\n\n")
            
            for table, columns in table_structures.items():
                f.write(f"Table: {table}\n")
                f.write("-" * (len(table) + 7) + "\n")
                
                for col in columns:
                    nullable = "NULL" if col['nullable'].lower() == 'yes' else "NOT NULL"
                    f.write(f"  {col['name']} - {col['type']} {nullable}\n")
                    
                f.write("\n")
        
        logger.info(f"Database structure saved to {output_dir}")
    except Exception as e:
        logger.error(f"Error visualizing table structure: {e}")
        logger.error(traceback.format_exc())

def visualize_table_relationships(db, output_dir: str) -> None:
    """
    Visualize relationships between tables
    
    Args:
        db: Database connector
        output_dir: Directory to save output files
    """
    try:
        # Get foreign key relationships
        fk_query = """
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name
        """
        relationships = db.query(fk_query)
        
        if not relationships:
            logger.warning("No foreign key relationships found in database")
            return
            
        # Process relationships
        relation_list = []
        for rel in relationships:
            if isinstance(rel, tuple) and len(rel) >= 4:
                relation_list.append({
                    'source_table': rel[0],
                    'source_column': rel[1],
                    'target_table': rel[2],
                    'target_column': rel[3]
                })
            elif isinstance(rel, dict):
                relation_list.append({
                    'source_table': rel.get('source_table', 'unknown'),
                    'source_column': rel.get('source_column', 'unknown'),
                    'target_table': rel.get('target_table', 'unknown'),
                    'target_column': rel.get('target_column', 'unknown')
                })
                
        # Save relationships as text file
        with open(os.path.join(output_dir, 'table_relationships.txt'), 'w') as f:
            f.write("TABLE RELATIONSHIPS\n")
            f.write("==================\n\n")
            
            for rel in relation_list:
                f.write(f"{rel['source_table']}.{rel['source_column']} -> {rel['target_table']}.{rel['target_column']}\n")
                
        # Try to visualize the relationships as a simple diagram
        try:
            import networkx as nx
            from matplotlib.lines import Line2D
            
            # Create a graph
            G = nx.DiGraph()
            
            # Add nodes (tables)
            tables = set()
            for rel in relation_list:
                tables.add(rel['source_table'])
                tables.add(rel['target_table'])
                
            for table in tables:
                G.add_node(table)
                
            # Add edges (relationships)
            for rel in relation_list:
                G.add_edge(rel['source_table'], rel['target_table'], 
                          source_col=rel['source_column'], 
                          target_col=rel['target_column'])
                
            # Create figure
            plt.figure(figsize=(12, 10))
            
            # Use a layout that spaces nodes nicely
            pos = nx.spring_layout(G, seed=42)
            
            # Draw nodes
            nx.draw_networkx_nodes(G, pos, node_size=3000, node_color='lightblue', alpha=0.8)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, arrowsize=20)
            
            # Draw labels
            nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
            
            # Draw edge labels
            edge_labels = {}
            for u, v, data in G.edges(data=True):
                edge_labels[(u, v)] = f"{data['source_col']} → {data['target_col']}"
                
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
            
            plt.title("Database Table Relationships", fontsize=16)
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'table_relationships.png'), dpi=120)
            plt.close()
            
        except ImportError:
            logger.warning("NetworkX library not available, skipping relationship diagram")
            # Create a simple text-based diagram
            plt.figure(figsize=(12, 10))
            plt.axis('off')
            
            plt.text(0.5, 0.98, "Database Table Relationships", 
                    fontsize=16, ha='center', fontweight='bold')
            
            y_position = 0.90
            line_height = 0.04
            
            for rel in relation_list:
                plt.text(0.1, y_position, 
                        f"{rel['source_table']}.{rel['source_column']} → {rel['target_table']}.{rel['target_column']}", 
                        fontsize=10, fontfamily='monospace')
                y_position -= line_height
                
            plt.savefig(os.path.join(output_dir, 'table_relationships_simple.png'), dpi=120)
            plt.close()
            
        logger.info(f"Table relationships saved to {output_dir}")
    except Exception as e:
        logger.error(f"Error visualizing table relationships: {e}")
        logger.error(traceback.format_exc())

def visualize_sample_data(db, output_dir: str, days: int = 7) -> None:
    """
    Visualize sample data from tables
    
    Args:
        db: Database connector
        output_dir: Directory to save output files
        days: Number of days to look back for data
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for SQL
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Check for tables we expect to have
        tables_to_check = ['devices', 'plants', 'inverter_details']
        
        for table in tables_to_check:
            # Check if table exists and has data
            count_query = f"SELECT COUNT(*) FROM {table}"
            
            try:
                count_result = db.query(count_query)
                
                # Handle different result formats from database connector
                if isinstance(count_result, list) and len(count_result) > 0:
                    if isinstance(count_result[0], tuple) and len(count_result[0]) > 0:
                        count = count_result[0][0]  # List of tuples
                    elif isinstance(count_result[0], dict) and 'count' in count_result[0]:
                        count = count_result[0]['count']  # List of dicts with 'count' key
                    else:
                        # Try to convert first item to int
                        try:
                            count = int(count_result[0])
                        except (TypeError, ValueError):
                            logger.warning(f"Couldn't determine count for table {table}, skipping")
                            continue
                elif isinstance(count_result, dict) and 'count' in count_result:
                    count = count_result['count']  # Direct dict with 'count' key
                else:
                    logger.warning(f"Unexpected count result format for table {table}: {count_result}")
                    continue
                
                logger.info(f"Table {table} has {count} rows")
                
                # Get a sample of data from the table
                if table == 'inverter_details':
                    # For inverter_details, get data from the date range
                    sample_query = f"""
                        SELECT * FROM {table}
                        WHERE collected_at BETWEEN %s AND %s
                        ORDER BY collected_at DESC
                        LIMIT 100
                    """
                    sample_data = db.query(sample_query, (start_date_str, end_date_str))
                else:
                    # For other tables, just get a sample
                    sample_query = f"SELECT * FROM {table} LIMIT 50"
                    sample_data = db.query(sample_query)
                
                if not sample_data:
                    logger.warning(f"No sample data found for table {table}")
                    continue
                    
                # Get column names
                columns_query = f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """
                columns_result = db.query(columns_query)
                
                # Process column names from the result
                column_names = []
                if columns_result:
                    # Handle different result formats
                    if isinstance(columns_result[0], tuple):
                        column_names = [col[0] for col in columns_result]
                    elif isinstance(columns_result[0], dict) and 'column_name' in columns_result[0]:
                        column_names = [col['column_name'] for col in columns_result]
                    else:
                        # Try to extract names generically
                        for col in columns_result:
                            if hasattr(col, '__getitem__'):
                                try:
                                    column_names.append(col[0])
                                except (IndexError, TypeError):
                                    column_names.append(str(col))
                            else:
                                column_names.append(str(col))
                
                if not column_names:
                    logger.warning(f"Could not retrieve column names for table {table}")
                    continue
                
                # Convert sample data to a standard format for pandas
                standardized_data = []
                
                # Handle sample data based on its format
                if isinstance(sample_data[0], dict):
                    # Data is already in dict format, extract values in column order
                    for row_dict in sample_data:
                        row_values = []
                        for col in column_names:
                            row_values.append(row_dict.get(col, None))
                        standardized_data.append(row_values)
                elif isinstance(sample_data[0], tuple):
                    # Data is in tuple format, use as is
                    standardized_data = sample_data
                else:
                    # Unexpected format, try to handle generically
                    for row in sample_data:
                        if hasattr(row, '__iter__') and not isinstance(row, (str, bytes, dict)):
                            standardized_data.append(list(row))
                        else:
                            # Can't process this format
                            logger.warning(f"Unexpected data format in table {table}, skipping")
                            continue
                
                # Create DataFrame with the standardized data
                df = pd.DataFrame(standardized_data, columns=column_names)
                
                # Save sample data to CSV for analysis
                csv_path = os.path.join(output_dir, f'{table}_sample.csv')
                df.to_csv(csv_path, index=False)
                logger.info(f"Saved sample data to {csv_path}")
                
                # Continue with visualizations using the DataFrame
                # Visualize basic statistics for the table
                plt.figure(figsize=(14, 8))
                plt.axis('off')
                
                plt.text(0.5, 0.98, f"Table: {table} - Data Summary", 
                        fontsize=16, ha='center', fontweight='bold')
                
                # Show table info
                info_str = []
                info_str.append(f"Total rows: {count}")
                info_str.append(f"Sample size: {len(df)}")
                info_str.append(f"Columns: {len(column_names)}")
                
                plt.text(0.5, 0.92, "\n".join(info_str), 
                        fontsize=12, ha='center')
                
                # Show column statistics
                stats_text = []
                stats_text.append(f"{'Column':<20} {'Type':<10} {'Non-Null':<10} {'Unique Values':<15}")
                stats_text.append("-" * 60)
                
                for col in df.columns:
                    col_type = str(df[col].dtype)
                    non_null = df[col].count()
                    try:
                        unique = df[col].nunique()
                    except:
                        unique = "N/A"
                    
                    stats_text.append(f"{str(col)[:18]:<20} {col_type:<10} {non_null:<10} {unique:<15}")
                
                plt.text(0.1, 0.85, "\n".join(stats_text), 
                        fontsize=10, fontfamily='monospace', va='top')
                
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, f'{table}_summary.png'), dpi=120)
                plt.close()
                
                # For numeric columns, create histograms
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                
                if numeric_cols:
                    # Limit to 10 columns max
                    if len(numeric_cols) > 10:
                        numeric_cols = numeric_cols[:10]
                        
                    n_cols = min(3, len(numeric_cols))
                    n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
                    
                    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 5, n_rows * 4))
                    if n_rows * n_cols == 1:
                        axes = np.array([axes])  # Make it indexable for single plot
                    axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
                    
                    for i, col in enumerate(numeric_cols):
                        ax = axes[i]
                        try:
                            df[col].hist(ax=ax, bins=20)
                            ax.set_title(f"{col} Distribution")
                            ax.set_xlabel(col)
                            ax.set_ylabel("Frequency")
                        except Exception as e:
                            logger.warning(f"Could not create histogram for column {col}: {e}")
                            ax.text(0.5, 0.5, f"Error: {str(e)}", ha='center', va='center')
                            ax.set_title(f"{col} - Error")
                        
                    # Hide unused subplots
                    for j in range(len(numeric_cols), len(axes)):
                        axes[j].axis('off')
                        
                    plt.tight_layout()
                    plt.savefig(os.path.join(output_dir, f'{table}_numeric_distributions.png'), dpi=120)
                    plt.close()
                
                # For inverter_details, create a time series plot
                if table == 'inverter_details' and any(col in df.columns for col in ['collected_at', 'last_update_time']):
                    # Determine which timestamp column to use
                    timestamp_col = 'collected_at' if 'collected_at' in df.columns else 'last_update_time'
                    
                    try:
                        # Convert timestamp to datetime
                        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
                        
                        # Find energy columns
                        energy_cols = [col for col in df.columns if 'energy' in str(col).lower()]
                        
                        if energy_cols:
                            plt.figure(figsize=(14, 8))
                            
                            for col in energy_cols:
                                try:
                                    # Convert to numeric and sort by time
                                    df_plot = df.sort_values(timestamp_col)
                                    df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
                                    
                                    # Skip if all values are NaN
                                    if df_plot[col].isna().all():
                                        logger.warning(f"All values in column {col} are NaN, skipping")
                                        continue
                                        
                                    # Plot the time series
                                    plt.plot(df_plot[timestamp_col], df_plot[col], marker='o', label=col)
                                except Exception as e:
                                    logger.warning(f"Could not plot {col}: {e}")
                                    
                            plt.title(f"{table} - Energy Values Over Time")
                            plt.xlabel("Date/Time")
                            plt.ylabel("Energy")
                            plt.legend()
                            plt.grid(True)
                            plt.tight_layout()
                            plt.savefig(os.path.join(output_dir, f'{table}_energy_timeseries.png'), dpi=120)
                            plt.close()
                    except Exception as e:
                        logger.error(f"Error creating time series plot for {table}: {e}")
                        
            except Exception as e:
                logger.error(f"Error analyzing table {table}: {e}")
                logger.error(traceback.format_exc())
                
        logger.info(f"Sample data analysis saved to {output_dir}")
    except Exception as e:
        logger.error(f"Error visualizing sample data: {e}")
        logger.error(traceback.format_exc())

def main():
    parser = argparse.ArgumentParser(description="Database Visualizer for Growatt Devices Monitor")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back for data")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--output", type=str, default="db_analysis", help="Output directory for visualizations")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Create output directory
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Import the database connector
        try:
            from app.database import DatabaseConnector
            db = DatabaseConnector()
        except ImportError:
            logger.error("Could not import DatabaseConnector from app.database")
            return 1
        except Exception as e:
            logger.error(f"Could not initialize database connector: {e}")
            return 1
        
        # Run analysis functions
        visualize_table_structure(db, output_dir)
        visualize_table_relationships(db, output_dir)
        visualize_sample_data(db, output_dir, args.days)
        
        logger.info(f"All database visualizations completed successfully. Output saved to {output_dir}")
        return 0
    except Exception as e:
        logger.error(f"Error during database visualization: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
