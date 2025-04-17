import pathlib
import numpy as np
import argparse
import os
import sys
import matplotlib.pyplot as plt
import glob
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Fix the import path
# Add the project root to the path
current_file = pathlib.Path(__file__)
project_root = current_file.parent.parent.parent.parent
sys.path.append(str(project_root))

from app.ml.data_preprocessing import load_data, create_features, prepare_lstm_data
from app.ml.models.pvlib_model import PVLibModel
from app.ml.models.lstm_model import create_lstm_model, train_lstm_model
from app.ml.models.hybrid_model import HybridPVForecaster

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

def main(data_path=None, output_dir="./model_output", lat=None, lon=None, alt=0):
    """
    Train the hybrid PV forecasting model.
    
    Args:
        data_path: Path to the CSV data file or directory. If None, search for CSV files.
        output_dir: Directory to save the model and results
        lat, lon: Latitude and longitude of the system
        alt: Altitude in meters
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Define target column for prediction - using the correct column name from the dataset
    target_column = 'output_watt'
    
    # 1. Load and preprocess data
    print("Loading and preprocessing data...")
    # Use the data folder path
    data_folder = os.path.join(project_root, 'data')
    
    # If data_path is not provided or is a directory, search for CSV files
    if data_path is None:
        csv_files = find_csv_files()
        if not csv_files:
            raise ValueError("No CSV files found in the data directory. Please provide a path to a CSV file.")
        print(f"Found {len(csv_files)} CSV files in the data directory.")
        for i, file in enumerate(csv_files):
            print(f"{i+1}. {os.path.basename(file)}")
        
        selected = 0
        if len(csv_files) > 1:
            while selected < 1 or selected > len(csv_files):
                try:
                    selected = int(input(f"Please select a file (1-{len(csv_files)}): "))
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            data_file = csv_files[selected-1]
        else:
            data_file = csv_files[0]
        
        print(f"Using data file: {data_file}")
    elif os.path.isdir(data_path):
        csv_files = find_csv_files(data_path)
        if not csv_files:
            raise ValueError(f"No CSV files found in directory {data_path}")
        print(f"Found {len(csv_files)} CSV files in directory {data_path}")
        for i, file in enumerate(csv_files):
            print(f"{i+1}. {os.path.basename(file)}")
        
        selected = 0
        if len(csv_files) > 1:
            while selected < 1 or selected > len(csv_files):
                try:
                    selected = int(input(f"Please select a file (1-{len(csv_files)}): "))
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            data_file = csv_files[selected-1]
        else:
            data_file = csv_files[0]
        
        print(f"Using data file: {data_file}")
    else:
        # Check if file exists in the data folder, otherwise use the original path
        data_file = os.path.join(data_folder, os.path.basename(data_path))
        if not os.path.exists(data_file):
            data_file = data_path
    
    df = load_data(data_file)
    
    # Print columns to help debug
    print(f"Available columns in dataset: {df.columns.tolist()}")
    
    # Verify target column exists
    if target_column not in df.columns:
        raise KeyError(f"Target column '{target_column}' not found in dataset. Available columns: {df.columns.tolist()}")
    
    df_features = create_features(df)
    
    # Features for the LSTM model
    feature_columns = [
        'voltage', 'current', 'ghi', 'temp_air', 'wind_speed',
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
    ]
    
    # If lat and lon are not provided, prompt for them
    if lat is None or lon is None:
        print("Latitude and longitude are required for PVLib model.")
        lat = float(input("Enter latitude: ")) if lat is None else lat
        lon = float(input("Enter longitude: ")) if lon is None else lon
    
    # 2. Prepare data for LSTM
    print("Preparing data for LSTM model...")
    X_train, X_val, X_test, y_train, y_val, y_test, scalers = prepare_lstm_data(
        df_features, feature_columns, target_column
    )
    
    # 3. Initialize and train the LSTM model
    print("Training LSTM model...")
    input_shape = (X_train.shape[1], X_train.shape[2])
    lstm_model = create_lstm_model(input_shape)
    
    trained_lstm, history = train_lstm_model(
        lstm_model, X_train, y_train, X_val, y_val, 
        epochs=100, batch_size=32
    )
    
    # 4. Initialize the PVLib model
    print("Setting up PVLib model...")
    module_params, inverter_params, system_params = PVLibModel.estimate_parameters_from_data(df)
    
    # Add required temperature model parameters
    system_params['module_type'] = 'glass_glass'  # Options: 'glass_glass', 'glass_polymer'
    system_params['racking_model'] = 'open_rack'  # Options: 'open_rack', 'close_mount', 'insulated_back'
    
    pvlib_model = PVLibModel(
        latitude=lat, 
        longitude=lon, 
        altitude=alt,
        module_parameters=module_params,
        inverter_parameters=inverter_params,
        system_parameters=system_params
    )
    
    # 5. Generate PVLib predictions for the historical data
    print("Generating PVLib predictions...")
    weather_data = df[['ghi', 'temp_air', 'wind_speed']]
    pvlib_predictions = pvlib_model.predict(weather_data)
    
    # 6. Create and train the hybrid model
    print("Training hybrid model...")
    hybrid_model = HybridPVForecaster(
        pvlib_model=pvlib_model,
        lstm_model=trained_lstm,
        feature_scaler=scalers['feature'],
        target_scaler=scalers['target']
    )
    
    hybrid_model.train_blending_model(
        historical_data=df_features,
        features=feature_columns,
        target=target_column,
        pvlib_predictions=pvlib_predictions
    )
    
    # 7. Evaluate models on test set
    print("Evaluating models...")
    # Prepare test data for prediction in the correct format
    test_indices = range(len(X_train) + len(X_val), len(X_train) + len(X_val) + len(X_test))
    test_dates = df_features.index[test_indices]
    
    test_weather = df_features.loc[test_dates, ['ghi', 'temp_air', 'wind_speed']]
    test_features = df_features.loc[test_dates, feature_columns]
    
    # Get predictions from hybrid model
    hybrid_predictions = hybrid_model.predict(test_weather, test_features)
    # Calculate evaluation metrics
    actual_values = df_features.loc[test_dates[-len(hybrid_predictions):], target_column]
    
    # Calculate evaluation metrics
    mae_lstm = mean_absolute_error(actual_values, hybrid_predictions['lstm_prediction'])
    mae_pvlib = mean_absolute_error(actual_values, hybrid_predictions['pvlib_prediction'])
    mae_hybrid = mean_absolute_error(actual_values, hybrid_predictions['hybrid_prediction'])
    
    rmse_lstm = np.sqrt(mean_squared_error(actual_values, hybrid_predictions['lstm_prediction']))
    rmse_pvlib = np.sqrt(mean_squared_error(actual_values, hybrid_predictions['pvlib_prediction']))
    rmse_hybrid = np.sqrt(mean_squared_error(actual_values, hybrid_predictions['hybrid_prediction']))
    
    print(f"LSTM Model - MAE: {mae_lstm:.2f} W, RMSE: {rmse_lstm:.2f} W")
    print(f"PVLib Model - MAE: {mae_pvlib:.2f} W, RMSE: {rmse_pvlib:.2f} W")
    print(f"Hybrid Model - MAE: {mae_hybrid:.2f} W, RMSE: {rmse_hybrid:.2f} W")
    
    # 8. Save the model
    model_path = os.path.join(output_dir, 'pv_forecast_model')
    hybrid_model.save(model_path)
    print(f"Model saved to {model_path}")
    
    # Add additional logging for clarity
    print("Note: Model is now saved in the modern Keras format (.keras) instead of HDF5 (.h5)")
    
    # 9. Plot results
    plt.figure(figsize=(12, 6))
    plt.plot(actual_values.index, actual_values.values, label='Actual', color='black')
    plt.plot(hybrid_predictions.index, hybrid_predictions['lstm_prediction'], label='LSTM', alpha=0.7)
    plt.plot(hybrid_predictions.index, hybrid_predictions['pvlib_prediction'], label='PVLib', alpha=0.7)
    plt.plot(hybrid_predictions.index, hybrid_predictions['hybrid_prediction'], label='Hybrid', alpha=0.7)
    plt.title('PV System Output Forecasting')
    plt.xlabel('Date')
    plt.ylabel('Output Power (W)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'forecast_results.png'))
    
    # 10. Save evaluation results to file
    with open(os.path.join(output_dir, 'evaluation_results.txt'), 'w') as f:
        f.write("PV FORECASTING MODEL EVALUATION\n")
        f.write("===============================\n\n")
        f.write(f"LSTM Model - MAE: {mae_lstm:.2f} W, RMSE: {rmse_lstm:.2f} W\n")
        f.write(f"PVLib Model - MAE: {mae_pvlib:.2f} W, RMSE: {rmse_pvlib:.2f} W\n")
        f.write(f"Hybrid Model - MAE: {mae_hybrid:.2f} W, RMSE: {rmse_hybrid:.2f} W\n")
    
    print("\nTraining completed successfully!")
    print(f"Results saved to: {output_dir}")

def print_usage_instructions():
    """Print detailed instructions on how to use this script."""
    print("""
        HOW TO RUN THE TRAINING MODEL SCRIPT
        ===================================

        Basic usage:
        -----------
        python app/ml/models/train_model.py [arguments]

        Arguments:
        ---------
        --data      : Path to CSV data file or directory with CSV files (optional)
                    If not provided, the script will search for CSV files in the default data directory
        --output    : Directory to save model and results (default: ./model_output)
        --lat       : Latitude of the PV system location
        --lon       : Longitude of the PV system location
        --alt       : Altitude of the PV system in meters (default: 0)

        Examples:
        --------
        1. Basic run with automatic CSV file detection:
        python app/ml/models/train_model.py --lat 13.736717 --lon 100.523186

        2. Specify a CSV file:
        python app/ml/models/train_model.py --data /path/to/data.csv --lat 13.736717 --lon 100.523186

        3. Specify a directory containing CSV files:
        python app/ml/models/train_model.py --data /path/to/csv/directory --lat 13.736717 --lon 100.523186

        4. Specify output directory:
        python app/ml/models/train_model.py --data /path/to/data.csv --output ./my_models --lat 13.736717 --lon 100.523186

        Notes:
        -----
        - When running without --data, the script will search for CSV files in the project's data directory
        - When multiple CSV files are found, you will be prompted to select one
        - If latitude and longitude are not provided, you will be prompted to enter them
        - The trained model and evaluation results will be saved in the specified output directory
        """)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a hybrid PV forecasting model')
    parser.add_argument('--data', required=False, default=None, 
                        help='Path to CSV data file or directory containing CSV files')
    parser.add_argument('--output', default='./model_output', help='Output directory')
    parser.add_argument('--lat', type=float, help='Latitude of the PV system')
    parser.add_argument('--lon', type=float, help='Longitude of the PV system')
    parser.add_argument('--alt', type=float, default=0, help='Altitude of the PV system in meters')
    parser.add_argument('--help-extended', action='store_true', help='Show extended usage instructions')
    
    args = parser.parse_args()
    
    if args.help_extended:
        print_usage_instructions()
        sys.exit(0)
    
    try:
        main(args.data, args.output, args.lat, args.lon, args.alt)
    except KeyboardInterrupt:
        print("\nTraining cancelled by user.")
    except Exception as e:
        print(f"\nError during training: {str(e)}")
        print("\nFor help, use --help or --help-extended")
