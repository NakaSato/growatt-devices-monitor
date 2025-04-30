import numpy as np
import datetime


class EnergyPredictor:
    """
    A simple energy prediction model that forecasts solar energy production
    based on historical data and date/time features.
    """

    def __init__(self):
        self.is_trained = False
        self.model = None
        self.seasonal_patterns = {
            # Monthly seasonal factors (Northern hemisphere)
            1: 0.6,  # January
            2: 0.7,  # February
            3: 0.9,  # March
            4: 1.1,  # April
            5: 1.3,  # May
            6: 1.4,  # June
            7: 1.5,  # July
            8: 1.4,  # August
            9: 1.2,  # September
            10: 0.9,  # October
            11: 0.7,  # November
            12: 0.5,  # December
        }
        self.daily_pattern = {
            # Hourly production factors (0-23)
            0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0,  # No production at night
            6: 0.1,    # Sunrise
            7: 0.3,
            8: 0.5,
            9: 0.7,
            10: 0.85,
            11: 0.95,
            12: 1.0,   # Solar noon
            13: 0.95,
            14: 0.85,
            15: 0.7,
            16: 0.5,
            17: 0.3,
            18: 0.1,   # Sunset
            19: 0, 20: 0, 21: 0, 22: 0, 23: 0,  # No production at night
        }
        self.base_production = 20.0  # kWh baseline daily production
        self.capacity = 10.0  # Default system capacity in kW

    def train(self, historical_data=None):
        """
        Train the prediction model using historical data.
        If no data provided, will use simulated parameters.
        
        Args:
            historical_data (list): Optional list of energy production records
        
        Returns:
            bool: True if training was successful
        """
        # For now, just mark as trained even without real training
        self.is_trained = True
        
        # If real data is provided, could fit a more sophisticated model here
        if historical_data and len(historical_data) > 0:
            # Extract system capacity from historical data if available
            max_hourly = max([record.get('energy', 0) for record in historical_data])
            if max_hourly > 0:
                self.capacity = max(5.0, max_hourly * 1.2)  # Estimate capacity
                self.base_production = self.capacity * 5.0  # Estimate daily production
                
        return self.is_trained

    def predict(self, start_date, end_date, system_capacity=None):
        """
        Predict energy production for a date range.
        
        Args:
            start_date (datetime): Start date for prediction
            end_date (datetime): End date for prediction
            system_capacity (float): Optional system capacity in kW
            
        Returns:
            list: List of predictions, each containing date and energy values
        """
        if not self.is_trained:
            self.train()
            
        # Use provided capacity if available
        capacity = system_capacity if system_capacity else self.capacity
            
        # Generate predictions for each day
        predictions = []
        current_date = start_date
        while current_date <= end_date:
            # Get seasonal factor for this month
            month = current_date.month
            seasonal_factor = self.seasonal_patterns.get(month, 1.0)
            
            # Apply some randomness for weather variations
            weather_factor = 0.8 + np.random.random() * 0.4
            
            # Generate daily prediction
            daily_energy = self.base_production * seasonal_factor * weather_factor
            
            # Add some random noise
            daily_energy *= (0.9 + np.random.random() * 0.2)
            
            # Round to reasonable precision
            daily_energy = round(daily_energy, 2)
            
            predictions.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'energy': daily_energy,
                'confidence': 0.7 + np.random.random() * 0.2
            })
            
            # Move to next day
            current_date += datetime.timedelta(days=1)
            
        return predictions
    
    def predict_hourly(self, date):
        """
        Predict hourly energy production for a specific date.
        
        Args:
            date (datetime): The date to predict for
            
        Returns:
            list: Hourly predictions for the day
        """
        # Get the daily prediction first
        daily_pred = self.predict(date, date)[0]
        daily_energy = daily_pred['energy']
        
        # Generate hourly breakdown
        hourly_predictions = []
        for hour in range(24):
            # Get hourly factor
            hourly_factor = self.daily_pattern.get(hour, 0)
            
            # Calculate hourly energy
            hourly_energy = daily_energy * hourly_factor
            
            # Add some random noise (clouds, etc)
            noise_factor = 0.9 + np.random.random() * 0.2
            hourly_energy *= noise_factor
            
            # Round to reasonable precision
            hourly_energy = round(hourly_energy, 2)
            
            # Create timestamp
            timestamp = datetime.datetime(
                date.year, date.month, date.day, hour, 0, 0
            )
            
            hourly_predictions.append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
                'hour': hour,
                'energy': hourly_energy
            })
            
        return hourly_predictions