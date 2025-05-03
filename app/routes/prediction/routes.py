from flask import Blueprint, jsonify, request, send_file
from datetime import datetime, timedelta
import numpy as np
import logging
import os
import tempfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment
import matplotlib.pyplot as plt
import json

# Import the energy predictor
from app.ml.energy_predictor import EnergyPredictor
# Import the I-V curve diagnosis system
from app.ml.iv_curve_diagnosis import IVCurveDiagnosis

# Create blueprint
prediction_routes = Blueprint('prediction_routes', __name__)

# Initialize the energy predictor and I-V curve diagnosis system
energy_predictor = EnergyPredictor()
iv_diagnosis = IVCurveDiagnosis()

@prediction_routes.route('/api/predictions/energy', methods=['GET'])
def get_energy_predictions():
    """
    Get energy production predictions for a date range
    """
    try:
        # Get query parameters
        days = request.args.get('days', 7, type=int)
        start_date_str = request.args.get('start_date', None)
        end_date_str = request.args.get('end_date', None)
        
        # Parse dates or use defaults
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        else:
            start_date = today
            
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        else:
            end_date = today + timedelta(days=days)
            
        # Get predictions
        predictions = energy_predictor.predict(start_date, end_date)
        
        return jsonify({
            'status': 'success',
            'data': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'predictions': predictions
            }
        })
        
    except Exception as e:
        logging.error(f"Error in energy predictions API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@prediction_routes.route('/api/predictions/hourly', methods=['GET'])
def get_hourly_predictions():
    """
    Get hourly energy production predictions for a specific date
    """
    try:
        # Get query parameters
        date_str = request.args.get('date', None)
        
        # Parse date or use default
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
        # Get hourly predictions
        predictions = energy_predictor.predict_hourly(target_date)
        
        return jsonify({
            'status': 'success',
            'data': {
                'date': target_date.strftime('%Y-%m-%d'),
                'predictions': predictions
            }
        })
        
    except Exception as e:
        logging.error(f"Error in hourly predictions API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@prediction_routes.route('/api/predictions/generate-model', methods=['POST'])
def generate_prediction_model():
    """
    Generate or retrain the prediction model
    """
    try:
        # Get training data from request if provided
        data = request.get_json() or {}
        historical_data = data.get('historical_data', [])
        
        # Train the model
        success = energy_predictor.train(historical_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Prediction model trained successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to train prediction model'
            }), 500
            
    except Exception as e:
        logging.error(f"Error training prediction model: {str(e)}")
        return jsonify({'error': str(e)}), 500
