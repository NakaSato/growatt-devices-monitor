import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MinMaxScaler
import joblib

class HybridPVForecaster:
    def __init__(self, pvlib_model, lstm_model, feature_scaler, target_scaler, seq_length=24):
        """
        Hybrid model combining PVLib and LSTM for PV forecasting.
        
        Args:
            pvlib_model: Initialized PVLibModel instance
            lstm_model: Trained LSTM model
            feature_scaler: Scaler for features
            target_scaler: Scaler for target
            seq_length: Sequence length used for LSTM
        """
        self.pvlib_model = pvlib_model
        self.lstm_model = lstm_model
        self.feature_scaler = feature_scaler
        self.target_scaler = target_scaler
        self.seq_length = seq_length
        self.blender = None
    
    def train_blending_model(self, historical_data, features, target, pvlib_predictions):
        """
        Train a model to optimally blend PVLib and LSTM predictions.
        
        Args:
            historical_data: DataFrame with historical data
            features: List of feature columns for LSTM
            target: Target column name
            pvlib_predictions: PVLib model predictions
        """
        # Prepare the LSTM predictions
        X_seq = self._prepare_lstm_sequences(historical_data[features].values)
        
        # Get LSTM predictions
        lstm_predictions_scaled = self.lstm_model.predict(X_seq)
        lstm_predictions = self.target_scaler.inverse_transform(lstm_predictions_scaled)
        
        # Merge predictions (handling different array shapes)
        start_idx = self.seq_length
        end_idx = start_idx + len(lstm_predictions)
        
        # Extract actual values for the same period
        actual_values = historical_data[target].values[start_idx:end_idx]
        
        # Get corresponding PVLib predictions
        pvlib_values = pvlib_predictions.iloc[start_idx:end_idx]['pvlib_ac_power'].values.reshape(-1, 1)
        
        # Create input for blending model
        blend_features = np.hstack((
            lstm_predictions,
            pvlib_values
        ))
        
        # Train a Ridge regression model for blending
        self.blender = Ridge(alpha=0.1)
        self.blender.fit(blend_features, actual_values)
        
        print("Blend model trained successfully")
    
    def _prepare_lstm_sequences(self, data):
        """Prepare data sequences for LSTM prediction"""
        # Scale the data
        scaled_data = self.feature_scaler.transform(data)
        
        # Create sequences
        X = []
        for i in range(len(scaled_data) - self.seq_length):
            X.append(scaled_data[i:i+self.seq_length])
        
        return np.array(X)
    
    def predict(self, weather_data, historical_features):
        """
        Make predictions using the hybrid model.
        
        Args:
            weather_data: DataFrame with future weather data
            historical_features: DataFrame with past features for LSTM
            
        Returns:
            DataFrame with predictions
        """
        # Get PVLib predictions
        pvlib_preds = self.pvlib_model.predict(weather_data)
        
        # Prepare LSTM input
        X_seq = self._prepare_lstm_sequences(historical_features.values)
        
        # Get LSTM predictions
        lstm_preds_scaled = self.lstm_model.predict(X_seq)
        lstm_preds = self.target_scaler.inverse_transform(lstm_preds_scaled)
        
        # Combine predictions using the blending model
        blend_input = np.hstack((
            lstm_preds,
            pvlib_preds['pvlib_ac_power'].values[-len(lstm_preds):].reshape(-1, 1)
        ))
        
        hybrid_preds = self.blender.predict(blend_input)
        
        # Create result DataFrame
        result = pd.DataFrame({
            'timestamp': weather_data.index[-len(hybrid_preds):],
            'lstm_prediction': lstm_preds.flatten(),
            'pvlib_prediction': pvlib_preds['pvlib_ac_power'].values[-len(hybrid_preds):],
            'hybrid_prediction': hybrid_preds
        })
        
        result.set_index('timestamp', inplace=True)
        
        return result
    
    def save(self, filepath_prefix):
        """
        Save the hybrid model components.
        
        Args:
            filepath_prefix: Prefix for saving model files
        """
        # Save the LSTM model
        self.lstm_model.save(f"{filepath_prefix}_lstm.h5")
        
        # Save the blender model
        joblib.dump(self.blender, f"{filepath_prefix}_blender.joblib")
        
        # Save the scalers
        joblib.dump(self.feature_scaler, f"{filepath_prefix}_feature_scaler.joblib")
        joblib.dump(self.target_scaler, f"{filepath_prefix}_target_scaler.joblib")
        
        print(f"Model saved with prefix: {filepath_prefix}")
    
    @classmethod
    def load(cls, filepath_prefix, pvlib_model):
        """
        Load the hybrid model from saved files.
        
        Args:
            filepath_prefix: Prefix for saved model files
            pvlib_model: Initialized PVLibModel instance
            
        Returns:
            Loaded HybridPVForecaster instance
        """
        # Load the LSTM model
        lstm_model = tf.keras.models.load_model(f"{filepath_prefix}_lstm.h5")
        
        # Load the blender model
        blender = joblib.load(f"{filepath_prefix}_blender.joblib")
        
        # Load the scalers
        feature_scaler = joblib.load(f"{filepath_prefix}_feature_scaler.joblib")
        target_scaler = joblib.load(f"{filepath_prefix}_target_scaler.joblib")
        
        # Create instance
        instance = cls(pvlib_model, lstm_model, feature_scaler, target_scaler)
        instance.blender = blender
        
        return instance
