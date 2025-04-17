import pandas as pd
import numpy as np
import argparse
import os
import sys
import pathlib
import tensorflow as tf
import glob
from pvlib_model import PVLibModel
from hybrid_model import HybridPVForecaster
import matplotlib.pyplot as plt

# Fix the import path
# Add the project root to the path
current_file = pathlib.Path(__file__)
project_root = current_file.parent.parent.parent.parent
sys.path.append(str(project_root))

def find_csv_files(directory=None):
    """
    Find all CSV files in the specified directory or in the default data directory.
    
    Args:
        directory: Path to directory to search for CSV files
                  If None, use the default data directory
    
    Returns:
        List of CSV file paths
    """
    if directory is None:
        directory = os.path.join(project_root, 'data')
    
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} does not exist.")
        return []
    
    csv_files = glob.glob(os.path.join(directory, '*.csv'))
    return csv_files

def select_csv_file(files, purpose_description):
    """
    Present a list of CSV files to the user and let them select one.
    
    Args:
        files: List of file paths
        purpose_description: Description of what this file will be used for
    
    Returns:
        Selected file path
    """
    if not files:
        return None
    
    print(f"\nSelect a CSV file for {purpose_description}:")
    for i, file in enumerate(files):
        print(f"{i+1}. {os.path.basename(file)}")
    
    selected = 0
    if len(files) > 1:
        while selected < 1 or selected > len(files):
            try:
                selected = int(input(f"Please select a file (1-{len(files)}): "))
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        selected_file = files[selected-1]
    else:
        selected_file = files[0]
    
    print(f"Using file: {selected_file}")
    return selected_file

def load_forecast_weather(weather_path):
    """Load weather forecast data from CSV."""
    weather = pd.read_csv(weather_path, parse_dates=['timestamp'])
    weather.set_index('timestamp', inplace=True)
    
    return weather

def main(model_dir=None, weather_path=None, historical_data_path=None, output_path=None, lat=None, lon=None, alt=0):
    """
    Generate PV output forecasts using the hybrid model.
    
    Args:
        model_dir: Directory containing the saved model files
        weather_path: Path to CSV with weather forecast data
        historical_data_path: Path to CSV with recent historical PV system data
        output_path: Path to save forecast results
        lat, lon, alt: System location coordinates
    """
    data_folder = os.path.join(project_root, 'data')
    
    # Search for model directory if not provided
    if model_dir is None:
        model_dirs = [d for d in os.listdir(os.path.join(project_root)) if os.path.isdir(os.path.join(project_root, d)) and 'model' in d.lower()]
        if not model_dirs:
            model_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and 'model' in d.lower()]
            
        if model_dirs:
            print("\nSelect a model directory:")
            for i, dir_name in enumerate(model_dirs):
                print(f"{i+1}. {dir_name}")
            
            selected = 0
            if len(model_dirs) > 1:
                while selected < 1 or selected > len(model_dirs):
                    try:
                        selected = int(input(f"Please select a model directory (1-{len(model_dirs)}): "))
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                
                model_dir = os.path.join(project_root, model_dirs[selected-1])
            else:
                model_dir = os.path.join(project_root, model_dirs[0])
        else:
            raise ValueError("No model directory found. Please provide a path with --model argument.")
    
    # Search for weather forecast data if not provided
    if weather_path is None:
        weather_files = find_csv_files()
        weather_files = [f for f in weather_files if 'weather' in os.path.basename(f).lower() or 'forecast' in os.path.basename(f).lower()]
        
        if not weather_files:
            weather_files = find_csv_files()
        
        weather_path = select_csv_file(weather_files, "weather forecast data")
        if weather_path is None:
            raise ValueError("No weather forecast CSV files found. Please provide a path with --weather argument.")
    
    # Search for historical data if not provided
    if historical_data_path is None:
        historical_files = find_csv_files()
        historical_files = [f for f in historical_files if 'historical' in os.path.basename(f).lower() or 'history' in os.path.basename(f).lower()]
        
        if not historical_files:
            historical_files = [f for f in find_csv_files() if f not in [weather_path]]
        
        historical_data_path = select_csv_file(historical_files, "historical PV system data")
        if historical_data_path is None:
            raise ValueError("No historical data CSV files found. Please provide a path with --historical argument.")
    
    # Set default output path if not provided
    if output_path is None:
        output_dir = os.path.join(project_root, 'results')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'pv_forecast_results.csv')
        print(f"Output will be saved to {output_path}")
    
    # 1. Load weather forecast data
    print("Loading weather forecast data...")
    weather_forecast = load_forecast_weather(weather_path)
    
    # 2. Load historical data for sequence input
    print("Loading historical PV system data...")
    historical_data = pd.read_csv(historical_data_path, parse_dates=['timestamp'])
    historical_data.set_index('timestamp', inplace=True)
    
    # Add time features to historical data
    historical_data['hour'] = historical_data.index.hour
    historical_data['month'] = historical_data.index.month
    historical_data['hour_sin'] = np.sin(2 * np.pi * historical_data['hour'] / 24)
    historical_data['hour_cos'] = np.cos(2 * np.pi * historical_data['hour'] / 24)
    historical_data['month_sin'] = np.sin(2 * np.pi * historical_data['month'] / 12)
    historical_data['month_cos'] = np.cos(2 * np.pi * historical_data['month'] / 12)
    
    # Ask for lat/lon if not provided
    if lat is None or lon is None:
        print("\nLocation coordinates are required for the PVLib model.")
        lat = float(input("Enter latitude: ")) if lat is None else lat
        lon = float(input("Enter longitude: ")) if lon is None else lon
    
    # 3. Recreate PVLib model with system parameters
    print("Setting up PVLib model...")
    module_params = {
        'pdc0': 5000,  # DC power rating
        'gamma_pdc': -0.004,  # power temperature coefficient
        'module_type': 'glass_polymer',  # Add module type for temperature model
    }
    
    inverter_params = {
        'pdc0': 5000,  # DC power rating
        'pac0': 4600,  # AC power rating
        'eta_inv_nom': 0.96,  # Nominal inverter efficiency
    }
    
    system_params = {
        'surface_tilt': 20,  # degrees
        'surface_azimuth': 180,  # degrees, facing south
        'albedo': 0.2,  # ground reflectance
        'racking_model': 'open_rack',  # Add racking model for temperature model
    }
    
    pvlib_model = PVLibModel(
        latitude=lat, 
        longitude=lon, 
        altitude=alt,
        module_parameters=module_params,
        inverter_parameters=inverter_params,
        system_parameters=system_params
    )
    
    # 4. Load the hybrid model
    print("Loading hybrid forecasting model...")
    model_path = os.path.join(model_dir, 'pv_forecast_model')
    hybrid_model = HybridPVForecaster.load(model_path, pvlib_model)
    
    # 5. Define feature columns (must match the ones used during training)
    feature_columns = [
        'voltage', 'current', 'ghi', 'temp_air', 'wind_speed',
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
    ]
    
    # 6. Make forecasts
    print("Generating forecasts...")
    forecasts = hybrid_model.predict(
        weather_data=weather_forecast[['ghi', 'temp_air', 'wind_speed']],
        historical_features=historical_data[feature_columns]
    )
    
    # 7. Save forecasts to CSV
    forecasts.to_csv(output_path)
    print(f"Forecasts saved to {output_path}")
    
    # 8. Plot forecasts
    plt.figure(figsize=(12, 6))
    plt.plot(forecasts.index, forecasts['hybrid_prediction'], label='Hybrid Forecast', color='blue')
    plt.plot(forecasts.index, forecasts['lstm_prediction'], label='LSTM Forecast', color='green', alpha=0.6)
    plt.plot(forecasts.index, forecasts['pvlib_prediction'], label='PVLib Forecast', color='orange', alpha=0.6)
    plt.title('PV System Output Forecast')
    plt.xlabel('Date')
    plt.ylabel('Output Power (W)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    # Save the plot
    plot_path = os.path.splitext(output_path)[0] + '.png'
    plt.savefig(plot_path)
    print(f"Forecast plot saved to {plot_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate PV system output forecasts')
    parser.add_argument('--model', required=False, default=None, 
                        help='Directory containing saved model files')
    parser.add_argument('--weather', required=False, default=None, 
                        help='Path to weather forecast CSV')
    parser.add_argument('--historical', required=False, default=None, 
                        help='Path to historical PV data CSV')
    parser.add_argument('--output', required=False, default=None, 
                        help='Path to save forecast results')
    parser.add_argument('--lat', type=float, help='Latitude of the PV system')
    parser.add_argument('--lon', type=float, help='Longitude of the PV system')
    parser.add_argument('--alt', type=float, default=0, help='Altitude of the PV system in meters')
    
    args = parser.parse_args()
    
    try:
        main(args.model, args.weather, args.historical, args.output, args.lat, args.lon, args.alt)
    except KeyboardInterrupt:
        print("\nPrediction cancelled by user.")
    except Exception as e:
        print(f"\nError during prediction: {str(e)}")
