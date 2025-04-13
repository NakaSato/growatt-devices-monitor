import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os
from pathlib import Path
import logging
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model storage path
MODEL_DIR = Path(__file__).parent / "models"
os.makedirs(MODEL_DIR, exist_ok=True)

class EnergyPredictor:
    """Energy production prediction service using ML techniques."""
    
    def __init__(self, db_connector=None):
        """Initialize the predictor with database connection."""
        self.db_connector = db_connector
        self.model_path = MODEL_DIR / "energy_prediction_model.joblib"
        self.scaler_path = MODEL_DIR / "energy_prediction_scaler.joblib"
        self.model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained model if available, otherwise create a new one."""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                logger.info("Loading existing model and scaler")
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                return True
            else:
                logger.info("No existing model found, a new one will be trained with available data")
                return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def _save_model(self):
        """Save the trained model and scaler."""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Model and scaler saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def get_historical_data(self, plant_id, mix_sn, days=90):
        """Fetch historical energy data from the database."""
        if self.db_connector is None:
            # Use synthetic data for demo if no database is connected
            return self._generate_synthetic_data(days)
        
        try:
            # Query structure would depend on your database schema
            # This is a placeholder for actual database querying
            query = """
            SELECT date, daily_energy 
            FROM energy_stats 
            WHERE plant_id = %s AND mix_sn = %s 
            ORDER BY date DESC 
            LIMIT %s
            """
            result = self.db_connector.query(query, (plant_id, mix_sn, days))
            
            if not result:
                logger.warning(f"No historical data found for plant_id={plant_id}, mix_sn={mix_sn}")
                return self._generate_synthetic_data(days)
                
            # Convert to DataFrame
            df = pd.DataFrame(result, columns=['date', 'energy'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return self._generate_synthetic_data(days)
    
    def _generate_synthetic_data(self, days=90):
        """Generate synthetic data for demo purposes."""
        logger.info("Generating synthetic historical data")
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        dates = [start_date + timedelta(days=i) for i in range(days)]
        
        # Create realistic energy output pattern
        energy_values = []
        for i in range(days):
            # Base value
            base = 40 + np.random.normal(0, 5)
            
            # Seasonal component (more energy in summer)
            day_of_year = dates[i].timetuple().tm_yday
            seasonal = 15 * np.sin(2 * np.pi * day_of_year / 365 - np.pi/2) + 15
            
            # Weekly pattern (less energy on weekends)
            weekday = dates[i].weekday()
            weekly = -5 if weekday >= 5 else 0
            
            # Weather effect (random fluctuations)
            weather = np.random.normal(0, 8)
            
            # Calculate total and ensure it's not negative
            energy = max(0, base + seasonal + weekly + weather)
            energy_values.append(round(energy, 1))
        
        df = pd.DataFrame({
            'date': dates,
            'energy': energy_values
        })
        
        return df
    
    def _extract_features(self, df):
        """Extract features from the time series data."""
        # Create a copy to avoid modifying the original
        data = df.copy()
        
        # Extract date-based features
        data['day_of_week'] = data['date'].dt.dayofweek
        data['month'] = data['date'].dt.month
        data['day'] = data['date'].dt.day
        data['day_of_year'] = data['date'].dt.dayofyear
        
        # Add lag features (previous days' energy)
        for i in range(1, 8):
            data[f'energy_lag_{i}'] = data['energy'].shift(i)
        
        # Add rolling statistics
        data['rolling_mean_3'] = data['energy'].rolling(window=3).mean()
        data['rolling_mean_7'] = data['energy'].rolling(window=7).mean()
        data['rolling_std_7'] = data['energy'].rolling(window=7).std()
        
        # Drop rows with NaN values (due to lag features)
        data = data.dropna()
        
        # Features to use for prediction
        feature_columns = [
            'day_of_week', 'month', 'day', 'day_of_year',
            'energy_lag_1', 'energy_lag_2', 'energy_lag_3', 
            'energy_lag_4', 'energy_lag_5', 'energy_lag_6', 'energy_lag_7',
            'rolling_mean_3', 'rolling_mean_7', 'rolling_std_7'
        ]
        
        X = data[feature_columns]
        y = data['energy']
        
        return X, y, data
    
    def train_model(self, plant_id=None, mix_sn=None):
        """Train a new prediction model using historical data."""
        try:
            # Get historical data
            df = self.get_historical_data(plant_id, mix_sn)
            
            # Extract features
            X, y, _ = self._extract_features(df)
            
            if len(X) < 10:
                logger.warning("Not enough data for training")
                return False
            
            # Split data for training and testing
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Standardize features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            logger.info("Training new model...")
            self.model = RandomForestRegressor(
                n_estimators=100, 
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            logger.info(f"Model trained - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R²: {r2:.2f}")
            
            # Save the model
            self._save_model()
            
            return True
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False
    
    def predict_energy(self, plant_id=None, mix_sn=None, days=7):
        """
        Predict energy production for the next specified days.
        
        Args:
            plant_id: Plant identifier
            mix_sn: Device serial number
            days: Number of days to predict
            
        Returns:
            Dictionary with prediction data
        """
        try:
            # If no model is available, train a new one
            if self.model is None:
                logger.info("No model available, training a new one")
                training_success = self.train_model(plant_id, mix_sn)
                if not training_success:
                    return self._generate_fallback_prediction(days)
            
            # Get historical data
            hist_df = self.get_historical_data(plant_id, mix_sn)
            
            # Prepare data for prediction
            last_date = hist_df['date'].max()
            
            # Dates to predict
            prediction_dates = [last_date + timedelta(days=i+1) for i in range(days)]
            
            # Extract historical values for presentation
            recent_history = hist_df.sort_values('date', ascending=False).head(days)
            recent_history = recent_history.sort_values('date')
            historical_dates = recent_history['date'].tolist()
            historical_values = recent_history['energy'].tolist()
            
            # Predict each day one by one
            predictions = []
            lower_bounds = []
            upper_bounds = []
            
            # Create a copy to work with
            working_df = hist_df.copy()
            
            for next_date in prediction_dates:
                # Add the next date to predict
                new_row = pd.DataFrame({'date': [next_date], 'energy': [None]})
                working_df = pd.concat([working_df, new_row], ignore_index=True)
                
                # Extract features (this will handle creating lag features)
                latest_df = working_df.tail(15)  # Use the most recent data
                latest_df['day_of_week'] = latest_df['date'].dt.dayofweek
                latest_df['month'] = latest_df['date'].dt.month
                latest_df['day'] = latest_df['date'].dt.day
                latest_df['day_of_year'] = latest_df['date'].dt.dayofyear
                
                # Add lag features
                for i in range(1, 8):
                    latest_df[f'energy_lag_{i}'] = latest_df['energy'].shift(i)
                
                # Add rolling statistics based on available data
                latest_df['rolling_mean_3'] = latest_df['energy'].rolling(window=3).mean()
                latest_df['rolling_mean_7'] = latest_df['energy'].rolling(window=7).mean()
                latest_df['rolling_std_7'] = latest_df['energy'].rolling(window=7).std()
                
                # Get the row to predict (last row)
                pred_row = latest_df.iloc[-1:].copy()
                
                # Features for prediction
                feature_columns = [
                    'day_of_week', 'month', 'day', 'day_of_year',
                    'energy_lag_1', 'energy_lag_2', 'energy_lag_3', 
                    'energy_lag_4', 'energy_lag_5', 'energy_lag_6', 'energy_lag_7',
                    'rolling_mean_3', 'rolling_mean_7', 'rolling_std_7'
                ]
                
                X_pred = pred_row[feature_columns]
                
                # Scale features
                X_pred_scaled = self.scaler.transform(X_pred)
                
                # Make prediction
                prediction = self.model.predict(X_pred_scaled)[0]
                prediction = max(0, prediction)  # Ensure non-negative
                
                # Add uncertainty bounds (using bootstrapping with the random forest)
                predictions_all_trees = np.array([
                    tree.predict(X_pred_scaled)[0] 
                    for tree in self.model.estimators_
                ])
                
                std_dev = np.std(predictions_all_trees)
                lower_bound = max(0, prediction - 1.96 * std_dev)
                upper_bound = prediction + 1.96 * std_dev
                
                # Append the prediction
                predictions.append(round(prediction, 1))
                lower_bounds.append(round(lower_bound, 1))
                upper_bounds.append(round(upper_bound, 1))
                
                # Update the working dataframe with the prediction for the next iteration
                working_df.loc[working_df['date'] == next_date, 'energy'] = prediction
            
            # Format dates for display
            formatted_hist_dates = [d.strftime('%Y-%m-%d') for d in historical_dates]
            formatted_pred_dates = [d.strftime('%Y-%m-%d') for d in prediction_dates]
            
            # Prepare response
            result = {
                'dates': formatted_pred_dates,
                'predictions': predictions,
                'upper_bound': upper_bounds,
                'lower_bound': lower_bounds,
                'historical_dates': formatted_hist_dates,
                'historical': historical_values
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return self._generate_fallback_prediction(days)
    
    def _generate_fallback_prediction(self, days=7):
        """Generate a fallback prediction when the model fails."""
        logger.warning("Using fallback prediction")
        
        # Generate dates
        end_date = datetime.now().date()
        historical_dates = [(end_date - timedelta(days=i)) for i in range(days, 0, -1)]
        prediction_dates = [(end_date + timedelta(days=i+1)) for i in range(days)]
        
        # Generate synthetic values
        historical = [round(40 + np.random.normal(0, 5), 1) for _ in range(days)]
        predictions = [round(42 + np.random.normal(0, 6), 1) for _ in range(days)]
        lower_bounds = [max(0, p - 8) for p in predictions]
        upper_bounds = [p + 8 for p in predictions]
        
        # Format dates
        formatted_hist_dates = [d.strftime('%Y-%m-%d') for d in historical_dates]
        formatted_pred_dates = [d.strftime('%Y-%m-%d') for d in prediction_dates]
        
        return {
            'dates': formatted_pred_dates,
            'predictions': predictions,
            'upper_bound': upper_bounds,
            'lower_bound': lower_bounds,
            'historical_dates': formatted_hist_dates,
            'historical': historical
        }
