---

# PV System Output Forecasting with Hybrid Model

This project implements a hybrid forecasting approach for PV system output prediction, combining:

- Physics-based modeling with PVLib
- Deep learning with LSTM neural networks

## Features

- Load and preprocess PV system and weather data
- Create time-based features for better predictions
- Build and train an LSTM model for sequence-based prediction
- Integrate physics-based PVLib models for solar irradiance and PV output
- Create a hybrid model that combines both approaches for improved accuracy
- Save and load models for deployment
- Generate forecasts for future time periods

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pv-forecasting.git
cd pv-forecasting

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Dataset Structure

The system expects data with the following columns:

| Column      | Description                  | Unit      |
| ----------- | ---------------------------- | --------- |
| timestamp   | Time of measurement          | DateTime  |
| voltage     | PV array voltage             | Volts (V) |
| current     | PV array current             | Amps (A)  |
| output_watt | Inverter AC output power     | Watts (W) |
| yield       | Energy produced (cumulative) | kWh       |
| ghi         | Global horizontal irradiance | W/m²      |
| temp_air    | Ambient temperature          | °C        |
| wind_speed  | Wind speed                   | m/s       |

## Training the Model

To train the hybrid model:

```bash
python train_model.py --data=your_data.csv --output=./model_output --lat=35.12 --lon=-106.54 --alt=1500
```

Arguments:

- `--data`: Path to your PV system dataset CSV
- `--output`: Directory to save the trained model and results
- `--lat`, `--lon`: Latitude and longitude of your PV system
- `--alt`: Altitude of your system in meters (optional)

## Making Predictions

To make predictions with the trained model:

```bash
python predict.py --model=./model_output --weather=weather_forecast.csv --historical=recent_data.csv --output=forecasts.csv --lat=35.12 --lon=-106.54
```

Arguments:

- `--model`: Directory containing the trained model files
- `--weather`: Path to weather forecast data
- `--historical`: Path to recent historical PV data
- `--output`: Path to save the forecast results
- `--lat`, `--lon`, `--alt`: Same as for training

## Model Details

The hybrid approach combines:

1. **PVLib Physics-based Model**:

   - Models solar position, irradiance, module temperature
   - Calculates DC and AC power output based on PV system specifications
   - Accounts for tilt, orientation, and weather conditions

2. **LSTM Neural Network**:

   - Learns patterns from historical data
   - Captures complex non-linear relationships
   - Uses sequence-based prediction for time-series data

3. **Hybrid Blending**:
   - Combines predictions from both models
   - Uses machine learning to determine optimal weighting
   - Typically achieves better accuracy than either model alone

## Deployment

The trained model can be deployed on edge devices by using the saved model files. The model is saved in two formats:

- TensorFlow saved model format for the LSTM component
- Joblib serialization for the blending model and scalers
