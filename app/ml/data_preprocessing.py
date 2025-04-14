import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

def load_data(filepath):
    """Load PV system and weather data from CSV file."""
    df = pd.read_csv(filepath, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Check for missing values
    if df.isnull().sum().any():
        print(f"Missing values found: {df.isnull().sum()}")
        df = df.interpolate(method='time')
    
    return df

def create_features(df):
    """Create additional time-based features for the model."""
    df_copy = df.copy()
    
    # Time features
    df_copy['hour'] = df_copy.index.hour
    df_copy['day'] = df_copy.index.day
    df_copy['month'] = df_copy.index.month
    df_copy['day_of_year'] = df_copy.index.dayofyear
    df_copy['day_of_week'] = df_copy.index.dayofweek
    
    # Add sin and cos components to capture cyclical nature of time
    df_copy['hour_sin'] = np.sin(2 * np.pi * df_copy['hour'] / 24)
    df_copy['hour_cos'] = np.cos(2 * np.pi * df_copy['hour'] / 24)
    df_copy['month_sin'] = np.sin(2 * np.pi * df_copy['month'] / 12)
    df_copy['month_cos'] = np.cos(2 * np.pi * df_copy['month'] / 12)
    
    # Calculate derived features
    df_copy['power_calculated'] = df_copy['voltage'] * df_copy['current']
    df_copy['efficiency'] = np.where(df_copy['power_calculated'] > 0, 
                                    df_copy['output_watt'] / df_copy['power_calculated'], 
                                    0)
    
    return df_copy

def prepare_lstm_data(df, features, target, seq_length=24):
    """
    Prepare data for LSTM model with sequence input.
    
    Args:
        df: DataFrame with features and targets
        features: List of feature column names
        target: Target column name
        seq_length: Number of time steps in each sequence
        
    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test, scalers
    """
    # Scale the features and target
    feature_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()
    
    feature_data = feature_scaler.fit_transform(df[features])
    target_data = target_scaler.fit_transform(df[[target]])
    
    X, y = [], []
    
    # Create sequences
    for i in range(len(df) - seq_length):
        X.append(feature_data[i:i+seq_length])
        y.append(target_data[i+seq_length])
    
    X, y = np.array(X), np.array(y)
    
    # Split data chronologically
    train_size = int(len(X) * 0.7)
    val_size = int(len(X) * 0.15)
    
    X_train, y_train = X[:train_size], y[:train_size]
    X_val, y_val = X[train_size:train_size+val_size], y[train_size:train_size+val_size]
    X_test, y_test = X[train_size+val_size:], y[train_size+val_size:]
    
    scalers = {
        'feature': feature_scaler,
        'target': target_scaler
    }
    
    return X_train, X_val, X_test, y_train, y_val, y_test, scalers
