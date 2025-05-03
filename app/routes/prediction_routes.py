from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import numpy as np
import logging

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

@prediction_routes.route('/api/diagnostics/iv-curve', methods=['POST'])
def diagnose_iv_curve():
    """
    Diagnose PV module health based on I-V curve data
    
    Expected JSON payload:
    {
        "voltage": [v1, v2, ...],  // Array of voltage measurements [V]
        "current": [i1, i2, ...],  // Array of current measurements [A]
        "temperature": 25.0,       // Module temperature in Celsius (optional)
        "module_id": "abc123"      // Module identifier (optional)
    }
    """
    try:
        # Get data from request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Extract I-V curve data
        voltage = data.get('voltage')
        current = data.get('current')
        temperature = data.get('temperature', 25.0)
        module_id = data.get('module_id', 'unknown')
        
        # Validate inputs
        if not voltage or not current:
            return jsonify({'error': 'Voltage and current arrays are required'}), 400
            
        if len(voltage) != len(current):
            return jsonify({'error': 'Voltage and current arrays must have the same length'}), 400
            
        # Convert to numpy arrays
        voltage = np.array(voltage)
        current = np.array(current)
        
        # Perform diagnosis
        diagnosis_result = iv_diagnosis.diagnose(voltage, current, temperature)
        
        # Add timestamp and module ID to result
        diagnosis_result['timestamp'] = datetime.now().isoformat()
        diagnosis_result['module_id'] = module_id
        
        return jsonify({
            'status': 'success',
            'data': diagnosis_result
        })
        
    except Exception as e:
        logging.error(f"Error in I-V curve diagnosis API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@prediction_routes.route('/api/diagnostics/simulate-iv-curve', methods=['GET'])
def simulate_iv_curve():
    """
    Simulate an I-V curve with optional fault injection
    
    Query parameters:
    - fault: Optional fault type ('partial_shading', 'soiling', etc.)
    - i_ph: Photogenerated current [A] (default: 10.0)
    - i_0: Diode saturation current [A] (default: 1e-10)
    - r_s: Series resistance [Ω] (default: 0.1)
    - r_sh: Shunt resistance [Ω] (default: 100.0)
    - v_oc: Approximate open circuit voltage [V] (default: 40.0)
    """
    try:
        # Get query parameters
        fault = request.args.get('fault', None)
        i_ph = request.args.get('i_ph', 10.0, type=float)
        i_0 = request.args.get('i_0', 1e-10, type=float)
        r_s = request.args.get('r_s', 0.1, type=float)
        r_sh = request.args.get('r_sh', 100.0, type=float)
        v_oc = request.args.get('v_oc', 40.0, type=float)
        
        # Simulate the I-V curve
        voltage, current = iv_diagnosis.simulate_iv_curve(
            i_ph=i_ph,
            i_0=i_0,
            r_s=r_s,
            r_sh=r_sh,
            v_oc_approx=v_oc,
            fault=fault
        )
        
        # Convert numpy arrays to lists for JSON serialization
        voltage_list = voltage.tolist()
        current_list = current.tolist()
        
        # Calculate power
        power_list = (voltage * current).tolist()
        
        # Diagnose the simulated curve
        diagnosis_result = iv_diagnosis.diagnose(voltage, current)
        
        return jsonify({
            'status': 'success',
            'data': {
                'voltage': voltage_list,
                'current': current_list,
                'power': power_list,
                'fault_type': fault or 'normal',
                'diagnosis': diagnosis_result
            }
        })
        
    except Exception as e:
        logging.error(f"Error in I-V curve simulation API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@prediction_routes.route('/api/diagnostics/train-model', methods=['POST'])
def train_iv_diagnosis_model():
    """
    Train the I-V curve diagnosis model
    
    Expected JSON payload:
    {
        "training_data": [
            {
                "voltage": [v1, v2, ...],  // Array of voltage measurements [V]
                "current": [i1, i2, ...],  // Array of current measurements [A]
                "fault_type": "normal"     // Known fault type (label)
            },
            // ... more training samples ...
        ],
        "model_type": "svm"  // Optional model type (default: 'svm')
    }
    """
    try:
        # Get data from request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Extract training data
        training_data = data.get('training_data', [])
        model_type = data.get('model_type', 'svm')
        
        # Validate inputs
        if not training_data:
            return jsonify({'error': 'Training data is required'}), 400
            
        # Create a new diagnosis system with the specified model type
        global iv_diagnosis
        iv_diagnosis = IVCurveDiagnosis(model_type=model_type)
        
        # Train the model
        success = iv_diagnosis.train(training_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'I-V curve diagnosis model trained successfully',
                'model_type': model_type
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to train I-V curve diagnosis model'
            }), 500
            
    except Exception as e:
        logging.error(f"Error training I-V curve diagnosis model: {str(e)}")
        return jsonify({'error': str(e)}), 500