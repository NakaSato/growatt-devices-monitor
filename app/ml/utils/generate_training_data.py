import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import argparse
import matplotlib.pyplot as plt

def setup_directories(base_dir):
    """
    Create organized directory structure for output files.
    
    Args:
        base_dir: Base directory path
        
    Returns:
        Dictionary with paths to different output directories
    """
    dirs = {
        'synthetic': os.path.join(base_dir, 'synthetic'),
        'historical': os.path.join(base_dir, 'historical'),
        'forecast': os.path.join(base_dir, 'forecast'),
        'plots': os.path.join(base_dir, 'plots')
    }
    
    # Create directories if they don't exist
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        
    return dirs

def generate_synthetic_data(days=90, start_date=None, system_size_kw=5.0, output_dir=None):
    """
    Generate synthetic PV system data for training models.
    
    Args:
        days: Number of days of data to generate
        start_date: Starting date for the data (defaults to days before current date)
        system_size_kw: Size of the PV system in kW
        output_dir: Directory to save the output files
        
    Returns:
        DataFrame with synthetic data
    """
    # Set default start date if not provided
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=days)).date()
    elif isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    
    # Create date ranges with hourly timestamps
    timestamps = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        # Generate data points for daylight hours only (5am to 9pm)
        for hour in range(5, 22):
            for minute in [0, 15, 30, 45]:
                timestamps.append(datetime(
                    current_date.year, 
                    current_date.month, 
                    current_date.day, 
                    hour, minute
                ))
    
    # Convert to DataFrame
    df = pd.DataFrame({'timestamp': timestamps})
    
    # Extract time features
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['day'] = df['timestamp'].dt.day
    df['month'] = df['timestamp'].dt.month
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    # Generate synthetic Global Horizontal Irradiance (GHI)
    # Base pattern that peaks at noon
    df['hour_fraction'] = df['hour'] + df['minute']/60
    df['base_ghi'] = -((df['hour_fraction'] - 13.5) ** 2) + 900
    df['base_ghi'] = df['base_ghi'].clip(lower=0)
    
    # Seasonal adjustment (more sun in summer)
    north_hemisphere = True  # Set to False for southern hemisphere
    if north_hemisphere:
        df['seasonal_factor'] = 0.5 + 0.5 * np.sin((df['day_of_year'] - 172) * 2 * np.pi / 365)
    else:
        df['seasonal_factor'] = 0.5 + 0.5 * np.sin((df['day_of_year'] - 355) * 2 * np.pi / 365)
    
    # Weather effect (random clouds)
    # Generate random weather patterns with temporal correlation
    np.random.seed(42)  # For reproducibility
    weather_pattern = np.random.normal(0, 0.15, size=days)  # One weather seed per day
    
    # Assign weather factors to each timestamp
    df['day_idx'] = df['timestamp'].dt.date.apply(lambda x: (x - start_date).days).astype(int)
    df['weather_factor'] = df['day_idx'].apply(lambda x: 
        max(0.1, min(1.0, 1.0 - abs(weather_pattern[x])))
    )
    # Add some random fluctuation within each day
    df['weather_factor'] *= np.random.uniform(0.85, 1.15, size=len(df))
    df['weather_factor'] = df['weather_factor'].clip(lower=0.1, upper=1.0)
    
    # Calculate final GHI
    df['ghi'] = df['base_ghi'] * df['seasonal_factor'] * df['weather_factor']
    df['ghi'] = df['ghi'].clip(lower=0)
    
    # Generate temperature and wind speed
    # Temperature correlates with time of day and season
    df['temp_air'] = 15 + 10 * df['seasonal_factor'] + (df['hour_fraction'] - 5) * 0.8 
    df['temp_air'] += np.random.normal(0, 2, size=len(df))  # Add random fluctuation
    
    # Wind speed (random but with daily patterns)
    df['base_wind'] = 2 + 2 * np.sin(2 * np.pi * df['hour_fraction'] / 24)
    df['wind_speed'] = df['base_wind'] * np.random.uniform(0.5, 1.5, size=len(df))
    df['wind_speed'] = df['wind_speed'].clip(lower=0)
    
    # Calculate PV system output based on GHI, temperature and system parameters
    # Basic model: Output depends on GHI, temperature coefficient, and system size
    temp_coeff = -0.004  # Typical temperature coefficient (%/°C)
    conversion_efficiency = 0.175  # Conversion efficiency
    system_losses = 0.14  # System losses (inverter, wiring, etc.)
    
    # Calculate DC power (before inverter)
    df['dc_power'] = df['ghi'] * system_size_kw * conversion_efficiency
    
    # Temperature effect on efficiency
    df['temp_factor'] = 1 + temp_coeff * (df['temp_air'] - 25)  # Reference temp is 25°C
    df['dc_power'] *= df['temp_factor']
    
    # Apply system losses
    df['output_watt'] = df['dc_power'] * 1000 * (1 - system_losses)
    df['output_watt'] = df['output_watt'].clip(lower=0)
    
    # Calculate voltage and current (simplified model)
    nominal_voltage = 560.0  # Nominal DC voltage
    
    # Voltage varies with temperature
    df['voltage'] = nominal_voltage * (1 - 0.001 * (df['temp_air'] - 25))
    
    # Current calculated to match power
    df['current'] = np.where(df['voltage'] > 0, df['dc_power'] * 1000 / df['voltage'], 0)
    
    # Calculate cumulative energy (yield in kWh)
    # Each 15-minute interval contributes energy
    df['energy_interval'] = df['output_watt'] * 0.25 / 1000  # kWh for 15 minutes
    df['yield'] = df['energy_interval'].cumsum()
    
    # Select final columns and set timestamp as index
    final_columns = [
        'timestamp', 'voltage', 'current', 'output_watt', 'yield',
        'ghi', 'temp_air', 'wind_speed', 'energy_interval'  # Added 'energy_interval'
    ]
    result_df = df[final_columns].copy()
    result_df.set_index('timestamp', inplace=True)
    
    # Save the data if output directory is provided
    if output_dir:
        # Check if we're using organized directories
        if isinstance(output_dir, dict):
            output_file = os.path.join(output_dir['synthetic'], f"synthetic_pv_data_{start_date.strftime('%Y%m%d')}.csv")
            plots_dir = output_dir['plots']
            # Ensure directories exist
            os.makedirs(output_dir['synthetic'], exist_ok=True)
        else:
            # For backward compatibility with string paths
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"synthetic_pv_data_{start_date.strftime('%Y%m%d')}.csv")
            plots_dir = os.path.join(output_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)
            
        result_df.reset_index().to_csv(output_file, index=False)
        print(f"Saved synthetic data to: {output_file}")
        
        # Create visualization of the data
        visualize_data(result_df, plots_dir, start_date, system_size_kw)
    
    return result_df

def generate_historical_data(full_data, days=7, output_dir=None):
    """
    Extract recent data from the full synthetic dataset to use as historical data for prediction.
    
    Args:
        full_data: DataFrame with the complete synthetic data
        days: Number of recent days to extract as historical data
        output_dir: Directory to save the output file
        
    Returns:
        DataFrame with historical data
    """
    # Get the end date of the full dataset
    end_date = full_data.index.max()
    
    # Calculate the start date for historical data
    start_date = end_date - timedelta(days=days)
    
    # Extract the historical data subset
    historical_data = full_data[full_data.index >= start_date].copy()
    
    # Save the historical data if output directory is provided
    if output_dir:
        # Check if we're using organized directories
        if isinstance(output_dir, dict):
            dir_path = output_dir['historical']
        else:
            dir_path = output_dir
            
        os.makedirs(dir_path, exist_ok=True)
        output_file = os.path.join(dir_path, f"historical_data_{start_date.date().strftime('%Y%m%d')}.csv")
        historical_data.reset_index().to_csv(output_file, index=False)
        print(f"Saved historical data to: {output_file}")
    
    return historical_data

def generate_weather_forecast(historical_data, days_to_forecast=7, output_dir=None):
    """
    Generate weather forecast data based on historical patterns.
    
    Args:
        historical_data: DataFrame with historical data
        days_to_forecast: Number of days to forecast
        output_dir: Directory to save output
        
    Returns:
        DataFrame with forecast weather data
    """
    # Get the last date in historical data
    last_date = historical_data.index.max()
    
    # Generate timestamps for forecast period
    timestamps = []
    start_date = (last_date + timedelta(days=1)).date()
    
    for i in range(days_to_forecast):
        current_date = start_date + timedelta(days=i)
        # Generate data points for daylight hours only (5am to 9pm)
        for hour in range(5, 22):
            for minute in [0, 15, 30, 45]:
                timestamps.append(datetime(
                    current_date.year, 
                    current_date.month, 
                    current_date.day, 
                    hour, minute
                ))
    
    forecast_df = pd.DataFrame({'timestamp': timestamps})
    forecast_df.set_index('timestamp', inplace=True)
    
    # Extract time features
    forecast_df['hour'] = forecast_df.index.hour
    forecast_df['day_of_year'] = forecast_df.index.dayofyear
    forecast_df['hour_fraction'] = forecast_df['hour'] + forecast_df.index.minute/60
    
    # Generate forecast with seasonality similar to historical but with some randomness
    
    # Get monthly averages from historical data
    historical_monthly = historical_data.groupby(historical_data.index.month).agg({
        'ghi': 'mean',
        'temp_air': 'mean',
        'wind_speed': 'mean'
    })
    
    # Get hourly patterns from historical data
    historical_hourly = historical_data.groupby(historical_data.index.hour).agg({
        'ghi': 'mean',
        'temp_air': 'mean',
        'wind_speed': 'mean'
    })
    
    # Apply patterns to forecast with some randomness
    for month in forecast_df.index.month.unique():
        for hour in range(5, 22):
            # Filter data for this month and hour
            mask = (forecast_df.index.month == month) & (forecast_df['hour'] == hour)
            
            # Base values from historical patterns
            base_ghi = historical_hourly.loc[hour, 'ghi']
            base_temp = historical_hourly.loc[hour, 'temp_air']
            base_wind = historical_hourly.loc[hour, 'wind_speed']
            
            # Monthly adjustments
            if month in historical_monthly.index:
                month_factor_ghi = historical_monthly.loc[month, 'ghi'] / historical_monthly['ghi'].mean()
                month_factor_temp = historical_monthly.loc[month, 'temp_air'] / historical_monthly['temp_air'].mean()
                month_factor_wind = historical_monthly.loc[month, 'wind_speed'] / historical_monthly['wind_speed'].mean()
            else:
                # Default if month not in historical data
                month_factor_ghi = 1.0
                month_factor_temp = 1.0
                month_factor_wind = 1.0
            
            # Apply base values with randomness
            forecast_df.loc[mask, 'ghi'] = base_ghi * month_factor_ghi * np.random.uniform(0.7, 1.3, size=mask.sum())
            forecast_df.loc[mask, 'temp_air'] = base_temp * month_factor_temp * np.random.uniform(0.9, 1.1, size=mask.sum())
            forecast_df.loc[mask, 'wind_speed'] = base_wind * month_factor_wind * np.random.uniform(0.7, 1.3, size=mask.sum())
    
    # Clean up and ensure no negative values
    forecast_df['ghi'] = forecast_df['ghi'].clip(lower=0)
    forecast_df['temp_air'] = forecast_df['temp_air'].clip(lower=-10)
    forecast_df['wind_speed'] = forecast_df['wind_speed'].clip(lower=0)
    
    # Drop helper columns
    forecast_df = forecast_df[['ghi', 'temp_air', 'wind_speed']]
    
    # Save the forecast if output directory is provided
    if output_dir:
        # Check if we're using organized directories
        if isinstance(output_dir, dict):
            dir_path = output_dir['forecast']
        else:
            dir_path = output_dir
            
        os.makedirs(dir_path, exist_ok=True)
        output_file = os.path.join(dir_path, f"weather_forecast_{start_date.strftime('%Y%m%d')}.csv")
        forecast_df.reset_index().to_csv(output_file, index=False)
        print(f"Saved weather forecast to: {output_file}")
    
    return forecast_df

def visualize_data(df, output_dir, start_date, system_size_kw=5.0):
    """Create visualizations of the generated data."""
    # Create output directory for plots
    if isinstance(output_dir, dict):
        plots_dir = output_dir['plots']
    else:
        plots_dir = output_dir
        
    os.makedirs(plots_dir, exist_ok=True)
    
    # Sample the data to reduce plotting density (every hour)
    sampled_df = df.resample('1h').mean()  # Changed from '1H' to '1h'
    
    # Plot 1: Daily energy production
    plt.figure(figsize=(14, 8))
    
    # Daily sum of energy
    daily_energy = df['energy_interval'].resample('D').sum()
    
    plt.subplot(2, 2, 1)
    daily_energy.plot(kind='bar')
    plt.title('Daily Energy Production')
    plt.ylabel('Energy (kWh)')
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Plot 2: Power output through the day
    plt.subplot(2, 2, 2)
    days_to_plot = min(7, (df.index[-1] - df.index[0]).days)
    end_date = df.index[-1].date()
    start_plot_date = end_date - timedelta(days=days_to_plot)
    
    for i in range(days_to_plot):
        day = start_plot_date + timedelta(days=i)
        day_data = sampled_df[sampled_df.index.date == day]
        plt.plot(day_data.index.hour + day_data.index.minute/60, 
                 day_data['output_watt'] / 1000,
                 label=day.strftime('%Y-%m-%d'))
    
    plt.title('Power Output by Time of Day')
    plt.xlabel('Hour of Day')
    plt.ylabel('Power (kW)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Plot 3: GHI vs Power Output
    plt.subplot(2, 2, 3)
    plt.scatter(sampled_df['ghi'], sampled_df['output_watt']/1000, alpha=0.3)
    plt.title('GHI vs Power Output')
    plt.xlabel('GHI (W/m²)')
    plt.ylabel('Power (kW)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Plot 4: Temperature Effect
    plt.subplot(2, 2, 4)
    
    # Only consider daylight hours with significant power output
    day_data = sampled_df[sampled_df['output_watt'] > 100]
    normalized_power = day_data['output_watt'] / day_data['ghi'] / system_size_kw
    
    plt.scatter(day_data['temp_air'], normalized_power, alpha=0.3)
    plt.title('Temperature Effect on Conversion Efficiency')
    plt.xlabel('Air Temperature (°C)')
    plt.ylabel('Normalized Power Output')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, f"pv_system_overview_{start_date.strftime('%Y%m%d')}.png"))
    
    # Create a time series plot for a week
    plt.figure(figsize=(15, 10))
    
    # Get one week of data
    week_data = sampled_df.iloc[-24*7:]
    
    plt.subplot(3, 1, 1)
    week_data['output_watt'].plot()
    plt.title('Power Output (Last Week)')
    plt.ylabel('Power (W)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.subplot(3, 1, 2)
    week_data['ghi'].plot()
    plt.title('Solar Irradiance (Last Week)')
    plt.ylabel('GHI (W/m²)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.subplot(3, 1, 3)
    week_data['temp_air'].plot()
    plt.title('Temperature (Last Week)')
    plt.ylabel('Temperature (°C)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, f"weekly_time_series_{start_date.strftime('%Y%m%d')}.png"))
    
    plt.close('all')

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic PV system data for model training')
    parser.add_argument('--days', type=int, default=90, help='Number of days of historical data to generate')
    parser.add_argument('--forecast_days', type=int, default=7, help='Number of days to forecast')
    parser.add_argument('--historical_days', type=int, default=7, help='Number of recent days to extract as historical data')
    parser.add_argument('--start_date', type=str, help='Start date for historical data (YYYY-MM-DD)')
    parser.add_argument('--system_size', type=float, default=5.0, help='System size in kW')
    parser.add_argument('--output', type=str, default='./data', help='Output directory')
    
    args = parser.parse_args()
    
    # Setup directory structure
    if args.output:
        output_dirs = setup_directories(args.output)
    else:
        output_dirs = setup_directories('./data')
    
    # Generate historical data
    print(f"Generating {args.days} days of synthetic PV system data...")
    synthetic_data = generate_synthetic_data(
        days=args.days, 
        start_date=args.start_date, 
        system_size_kw=args.system_size,
        output_dir=output_dirs
    )
    
    # Extract recent days as historical data for prediction
    print(f"Extracting {args.historical_days} days of recent data as historical data...")
    _ = generate_historical_data(
        full_data=synthetic_data,
        days=args.historical_days,
        output_dir=output_dirs
    )
    
    # Generate weather forecast data
    print(f"Generating {args.forecast_days} days of weather forecast data...")
    _ = generate_weather_forecast(
        historical_data=synthetic_data,
        days_to_forecast=args.forecast_days,
        output_dir=output_dirs
    )
    
    print("Data generation complete!")
    print("Files saved to the following directories:")
    for dir_type, dir_path in output_dirs.items():
        print(f"  - {dir_type}: {dir_path}")

if __name__ == "__main__":
    main()
