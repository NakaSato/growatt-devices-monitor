import logging
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

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

def train_model(plant_id=None, mix_sn=None, tune_hyperparams=False):
    """Train the energy prediction model."""
    try:
        logger.info("Initializing the energy predictor...")
        predictor = EnergyPredictor()
        
        logger.info(f"Starting model training (hyperparameter tuning: {tune_hyperparams})...")
        success = predictor.train_model(plant_id, mix_sn, tune_hyperparams)
        
        if success:
            logger.info("Model training completed successfully")
            model_info = predictor.get_model_info()
            logger.info(f"Model metrics: MAE={model_info.get('mae')}, RMSE={model_info.get('rmse')}, R²={model_info.get('r2')}")
            
            # Print feature importance
            feature_importance = model_info.get('feature_importance', {})
            if feature_importance:
                logger.info("Feature importance:")
                for feature, importance in feature_importance.items():
                    logger.info(f"  {feature}: {importance:.4f}")
        else:
            logger.error("Model training failed")
        
        return success
    except Exception as e:
        logger.exception(f"Error in model training: {e}")
        return False

def main():
    """Command line interface for model training."""
    parser = argparse.ArgumentParser(description='Train the energy prediction model')
    parser.add_argument('--plant-id', type=str, help='Plant ID for training data')
    parser.add_argument('--mix-sn', type=str, help='Mix SN for training data')
    parser.add_argument('--tune', action='store_true', help='Perform hyperparameter tuning')
    
    args = parser.parse_args()
    
    logger.info("Starting model training process...")
    success = train_model(args.plant_id, args.mix_sn, args.tune)
    
    if success:
        logger.info("Model training completed successfully")
        sys.exit(0)
    else:
        logger.error("Model training failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
