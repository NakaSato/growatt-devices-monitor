import pandas as pd
import numpy as np
import argparse
import os
from pvlib_model import PVLibModel
from hybrid_model import HybridPVForecaster
import tensorflow as tf
import matplotlib.pyplot as plt

def load_forecast_weather(weather_path):
    """Load weather forecast data from CSV."""
    weather = pd.read_csv(weather_path, parse_dates=['timestamp'])
    weather.set_index('timestamp', inplace=True)
    
    return weather

def main(model_dir, weather_path, historical_data_path, output_path, lat, lon, alt):
    """
    Generate PV output forecasts using the hybrid model.
    
    Args:
        model_dir: Directory containing the saved model files
        weather_path: Path to CSV with weather forecast data
        historical_data_path: Path to CSV with recent historical PV system data
        output_path: Path to save forecast results
        lat, lon, alt: System location coordinates
    """
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
    
    # 3. Recreate PVLib model with system parameters
    print("Setting up PVLib model...")
    # For simplicity, we'll use dummy values; in a real app you should load saved parameters
    module_params = {
        'pdc0': 5000,  # DC power rating
        'gamma_pdc': -0.004,  # power temperature coefficient
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
    parser.add_argument('--model', required=True, help='Directory containing saved model files')
    parser.add_argument('--weather', required=True, help='Path to weather forecast CSV')
    parser.add_argument('--historical', required=True, help='Path to historical PV data CSV')
    parser.add_argument('--output', required=True, help='Path to save forecast results')
    parser.add_argument('--lat', type=float, required=True, help='Latitude of the PV system')
    parser.add_argument('--lon', type=float, required=True, help='Longitude of the PV system')
    parser.add_argument('--alt', type=float, default=0, help='Altitude of the PV system in meters')
    
    args = parser.parse_args()
    
    main(args.model, args.weather, args.historical, args.output, args.lat, args.lon, args.alt)
