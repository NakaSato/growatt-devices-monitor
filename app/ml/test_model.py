import logging
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Add parent directory to path to import modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

from app.ml.energy_predictor import EnergyPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_prediction(days=7, visualize=False):
    """Test the energy prediction model."""
    try:
        logger.info("Initializing the energy predictor...")
        predictor = EnergyPredictor()
        
        # Get model info
        model_info = predictor.get_model_info()
        logger.info(f"Using model version: {model_info.get('version', 'unknown')}")
        logger.info(f"Model metrics: MAE={model_info.get('mae')}, RMSE={model_info.get('rmse')}, R²={model_info.get('r2')}")
        
        # Make predictions
        logger.info(f"Making predictions for the next {days} days...")
        prediction_result = predictor.predict_energy(days=days)
        
        # Print predictions
        logger.info("Prediction results:")
        for i, (date, pred, lower, upper) in enumerate(zip(
            prediction_result['dates'], 
            prediction_result['predictions'],
            prediction_result['lower_bound'],
            prediction_result['upper_bound']
        )):
            uncertainty = upper - lower
            logger.info(f"  {date}: {pred:.1f} kWh (range: {lower:.1f}-{upper:.1f}, uncertainty: ±{uncertainty/2:.1f})")
        
        # Visualize if requested
        if visualize:
            visualize_prediction(prediction_result)
            
        return True
    except Exception as e:
        logger.exception(f"Error in testing model: {e}")
        return False

def visualize_prediction(prediction_result):
    """Visualize the prediction results."""
    try:
        # Create a figure
        plt.figure(figsize=(12, 6))
        
        # Plot historical data
        plt.plot(prediction_result['historical_dates'], 
                 prediction_result['historical'], 
                 'o-', color='blue', label='Historical')
        
        # Plot predictions
        plt.plot(prediction_result['dates'], 
                 prediction_result['predictions'], 
                 'o-', color='green', label='Predictions')
        
        # Plot uncertainty
        plt.fill_between(
            prediction_result['dates'],
            prediction_result['lower_bound'],
            prediction_result['upper_bound'],
            alpha=0.2,
            color='green',
            label='Uncertainty'
        )
        
        # Add labels and title
        plt.xlabel('Date')
        plt.ylabel('Energy (kWh)')
        plt.title('Energy Production Forecast')
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        
        # Save plot
        output_dir = Path(__file__).parent / "output"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_dir / f"prediction_{datetime.now().strftime('%Y%m%d')}.png")
        plt.close()
        
        logger.info(f"Visualization saved to {output_dir}")
    except Exception as e:
        logger.error(f"Error visualizing prediction: {e}")

def main():
    """Command line interface for model testing."""
    parser = argparse.ArgumentParser(description='Test the energy prediction model')
    parser.add_argument('--days', type=int, default=7, help='Number of days to predict')
    parser.add_argument('--visualize', action='store_true', help='Visualize the predictions')
    
    args = parser.parse_args()
    
    logger.info("Starting model testing process...")
    success = test_prediction(args.days, args.visualize)
    
    if success:
        logger.info("Model testing completed successfully")
        sys.exit(0)
    else:
        logger.error("Model testing failed")
        sys.exit(1)

if __name__ == "__main__":
    import os
    main()
