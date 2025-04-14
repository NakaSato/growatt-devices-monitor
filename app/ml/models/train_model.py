import pandas as pd
import numpy as np
import argparse
import os
from app.ml.data_preprocessing import load_data, create_features, prepare_lstm_data
from pvlib_model import PVLibModel
from lstm_model import create_lstm_model, train_lstm_model
from hybrid_model import HybridPVForecaster
import matplotlib.pyplot as plt

def main(data_path, output_dir, lat, lon, alt):
    """
    Train the hybrid PV forecasting model.
    
    Args:
        data_path: Path to the CSV data file
        output_dir: Directory to save the model and results
        lat, lon: Latitude and longitude of the system
        alt: Altitude in meters
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load and preprocess data
    print("Loading and preprocessing data...")
    df = load_data(data_path)
    df_features = create_features(df)
    
    # Features for the LSTM model
    feature_columns = [
        'voltage', 'current', 'ghi', 'temp_air', 'wind_speed',
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
    ]
    
    # Target column
    target_column = 'output_watt'
    
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
    
    # Get actual values
    actual_values = df_features.loc[test_dates[-len(hybrid_predictions):], target_column]
    
    # Calculate evaluation metrics
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a hybrid PV forecasting model')
    parser.add_argument('--data', required=True, help='Path to CSV data file')
    parser.add_argument('--output', default='./model_output', help='Output directory')
    parser.add_argument('--lat', type=float, required=True, help='Latitude of the PV system')
    parser.add_argument('--lon', type=float, required=True, help='Longitude of the PV system')
    parser.add_argument('--alt', type=float, default=0, help='Altitude of the PV system in meters')
    
    args = parser.parse_args()
    
    main(args.data, args.output, args.lat, args.lon, args.alt)
