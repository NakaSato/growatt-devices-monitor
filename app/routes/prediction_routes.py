import logging
from flask import Blueprint, jsonify, request, current_app
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta

from app.database import DatabaseConnector
from app.ml.energy_predictor import EnergyPredictor

# Create a Blueprint for prediction routes
prediction_routes = Blueprint('prediction', __name__, url_prefix='/api/prediction')

# Initialize database connector and energy predictor
db_connector = DatabaseConnector()
energy_predictor = EnergyPredictor(db_connector=db_connector)

@prediction_routes.route('/', methods=['GET'])
def get_predictions() -> Tuple[Dict[str, Any], int]:
    """
    Get energy production predictions for a plant
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with prediction data and status code
    """
    try:
        # Get parameters from request
        plant_id = request.args.get('plant_id')
        mix_sn = request.args.get('device_sn')
        days = int(request.args.get('days', 7))
        
        if not plant_id:
            return jsonify({"status": "error", "message": "Plant ID is required"}), 400
        
        # Get predictions from the ML model
        prediction_data = energy_predictor.predict_energy(plant_id, mix_sn, days)
        
        # Store predictions in the database
        for i, date in enumerate(prediction_data.get('dates', [])):
            try:
                db_connector.save_prediction(
                    plant_id=plant_id,
                    mix_sn=mix_sn,
                    prediction_date=date,
                    energy_predicted=prediction_data['predictions'][i],
                    lower_bound=prediction_data['lower_bound'][i],
                    upper_bound=prediction_data['upper_bound'][i]
                )
            except Exception as e:
                current_app.logger.error(f"Error saving prediction to database: {str(e)}")
        
        return jsonify(prediction_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in get_predictions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prediction_routes.route('/analyze', methods=['POST'])
def analyze_data() -> Tuple[Dict[str, Any], int]:
    """
    Analyze historical data to generate predictions
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with analysis results and status code
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        plant_id = data.get('plant_id')
        
        if not plant_id:
            return jsonify({"status": "error", "message": "Plant ID is required"}), 400
        
        # Retrain the model with latest data
        training_success = energy_predictor.train_model(plant_id, data.get('device_sn'))
        
        # Get historical data from database
        historical_data = db_connector.query("""
            SELECT date, daily_energy 
            FROM energy_stats 
            WHERE plant_id = ? 
            ORDER BY date DESC 
            LIMIT 30
        """, (plant_id,))
        
        # Calculate efficiency score based on recent production
        efficiency_score = 0.80  # Default value
        if historical_data:
            recent_days = min(7, len(historical_data))
            recent_avg = sum(record['daily_energy'] for record in historical_data[:recent_days]) / recent_days
            
            # Compare to expected production
            capacity = data.get('capacity', 0)
            if capacity > 0:
                # Simple efficiency calculation: actual / theoretical max * 100%
                # Theoretical max considers 5 peak sun hours per day on average
                theoretical_max = capacity * 5  # kWh
                efficiency_score = min(1.0, max(0.0, recent_avg / theoretical_max if theoretical_max > 0 else 0.8))
        
        # Generate suggestions based on efficiency score
        suggestions = []
        if efficiency_score < 0.6:
            suggestions.append("Your system is performing below expected levels. Consider a maintenance check.")
            suggestions.append("Clean solar panels to improve efficiency by up to 10%")
        elif efficiency_score < 0.8:
            suggestions.append("Consider cleaning solar panels to improve efficiency by 5%")
            suggestions.append("Check for partial shading that might be affecting performance")
        
        # Always provide at least one suggestion
        suggestions.append("Consider adjusting panel angle for optimal seasonal sunlight")
        
        analysis_result = {
            "status": "success",
            "message": "Analysis completed successfully",
            "efficiency_score": round(efficiency_score, 2),
            "training_success": training_success,
            "improvement_suggestions": suggestions,
            "data_points_analyzed": len(historical_data)
        }
        
        return jsonify(analysis_result), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in analyze_data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Add a route to store data from API
@prediction_routes.route('/store-data', methods=['POST'])
def store_api_data() -> Tuple[Dict[str, Any], int]:
    """
    Store data from the Growatt API for later use in predictions
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with status code
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Extract data types from the request
        plants = data.get('plants', [])
        devices = data.get('devices', [])
        energy_data = data.get('energy_data', [])
        weather_data = data.get('weather_data', [])
        
        # Store plants
        if plants:
            db_connector.save_plant_data(plants)
        
        # Store devices
        if devices:
            db_connector.save_device_data(devices)
        
        # Store energy data
        stored_energy_count = 0
        if energy_data:
            for record in energy_data:
                success = db_connector.save_energy_data(
                    plant_id=record.get('plant_id'),
                    mix_sn=record.get('device_sn'),
                    date=record.get('date'),
                    daily_energy=record.get('daily_energy', 0.0),
                    peak_power=record.get('peak_power')
                )
                if success:
                    stored_energy_count += 1
        
        # Store weather data
        stored_weather_count = 0
        if weather_data:
            for record in weather_data:
                success = db_connector.save_weather_data(
                    plant_id=record.get('plant_id'),
                    date=record.get('date'),
                    temperature=record.get('temperature'),
                    condition=record.get('condition')
                )
                if success:
                    stored_weather_count += 1
        
        return jsonify({
            "status": "success",
            "message": "Data stored successfully",
            "plants_stored": len(plants),
            "devices_stored": len(devices),
            "energy_records_stored": stored_energy_count,
            "weather_records_stored": stored_weather_count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error storing API data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
