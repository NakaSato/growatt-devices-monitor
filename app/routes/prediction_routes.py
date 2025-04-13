import logging
from flask import Blueprint, jsonify, request, current_app
from typing import Tuple, Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from app.database import DatabaseConnector
from app.ml.energy_predictor import EnergyPredictor

# Create a Blueprint for prediction routes
prediction_routes = Blueprint('prediction', __name__, url_prefix='/api/prediction')

# Initialize database connector and energy predictor
db_connector = DatabaseConnector()
energy_predictor = EnergyPredictor(db_connector=db_connector)

@prediction_routes.route('/a', methods=['GET'])
def get_predictions() -> Tuple[Dict[str, Any], int]:
    """
    Get energy production predictions for a plant
    
    Query parameters:
        plant_id: ID of the plant (required)
        device_sn: Serial number of the device (optional)
        days: Number of days to predict (default: 7)
    
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
        
        if days < 1 or days > 30:
            return jsonify({"status": "error", "message": "Days parameter must be between 1 and 30"}), 400
        
        # Get predictions from the ML model
        prediction_data = energy_predictor.predict_energy(plant_id, mix_sn, days)
        
        # Store predictions in the database
        stored_count = 0
        for i, date in enumerate(prediction_data.get('dates', [])):
            try:
                success = db_connector.save_prediction(
                    plant_id=plant_id,
                    mix_sn=mix_sn,
                    prediction_date=date,
                    energy_predicted=prediction_data['predictions'][i],
                    lower_bound=prediction_data['lower_bound'][i],
                    upper_bound=prediction_data['upper_bound'][i]
                )
                if success:
                    stored_count += 1
            except Exception as e:
                current_app.logger.error(f"Error saving prediction to database: {str(e)}")
        
        prediction_data['stored_predictions'] = stored_count
        return jsonify(prediction_data), 200
        
    except ValueError as ve:
        current_app.logger.error(f"Value error in get_predictions: {str(ve)}")
        return jsonify({"status": "error", "message": f"Invalid parameter: {str(ve)}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error in get_predictions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prediction_routes.route('/analyze', methods=['POST'])
def analyze_data() -> Tuple[Dict[str, Any], int]:
    """
    Analyze historical data to generate predictions
    
    Request body:
        plant_id: ID of the plant (required)
        device_sn: Serial number of the device (optional)
        capacity: Installed capacity of the plant in kW (optional)
    
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
    
    Request body:
        plants: List of plant data objects (optional)
        devices: List of device data objects (optional)
        energy_data: List of energy data records (optional)
        weather_data: List of weather data records (optional)
    
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
        
        result = {"status": "success", "message": "Data stored successfully"}
        
        # Store plants
        if plants:
            success = db_connector.save_plant_data(plants)
            result["plants_stored"] = len(plants) if success else 0
        else:
            result["plants_stored"] = 0
        
        # Store devices
        if devices:
            success = db_connector.save_device_data(devices)
            result["devices_stored"] = len(devices) if success else 0
        else:
            result["devices_stored"] = 0
        
        # Store energy data in batch for better performance
        stored_energy_count = 0
        if energy_data:
            stored_energy_count = db_connector.save_energy_data_batch(energy_data)
        result["energy_records_stored"] = stored_energy_count
        
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
        result["weather_records_stored"] = stored_weather_count
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Error storing API data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prediction_routes.route('/latest', methods=['GET'])
def get_latest_predictions() -> Tuple[Dict[str, Any], int]:
    """
    Get the latest energy production predictions for a plant from the database
    
    Query parameters:
        plant_id: The ID of the plant (required)
        device_sn: (Optional) The serial number of the device
        limit: (Optional) Maximum number of predictions to return (default: 7)
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with prediction data and status code
    """
    try:
        # Get parameters from request
        plant_id = request.args.get('plant_id')
        mix_sn = request.args.get('device_sn')
        limit = int(request.args.get('limit', 7))
        
        if not plant_id:
            return jsonify({"status": "error", "message": "Plant ID is required"}), 400
        
        if limit < 1 or limit > 30:
            return jsonify({"status": "error", "message": "Limit parameter must be between 1 and 30"}), 400
        
        # Build query based on parameters
        query = """
            SELECT prediction_date, energy_predicted, lower_bound, upper_bound
            FROM predictions
            WHERE plant_id = ?
        """
        params: List[Union[str, int]] = [plant_id]
        
        if mix_sn:
            query += " AND mix_sn = ?"
            params.append(mix_sn)
        
        query += " ORDER BY prediction_date ASC LIMIT ?"
        params.append(limit)
        
        # Execute the query
        predictions = db_connector.query(query, tuple(params))
        
        if not predictions:
            # Generate new predictions if none exist
            prediction_data = energy_predictor.predict_energy(plant_id, mix_sn, limit)
            return jsonify(prediction_data), 200
        
        # Format the result
        result = {
            "plant_id": plant_id,
            "device_sn": mix_sn,
            "dates": [],
            "predictions": [],
            "lower_bound": [],
            "upper_bound": []
        }
        
        for pred in predictions:
            result["dates"].append(pred["prediction_date"])
            result["predictions"].append(pred["energy_predicted"])
            result["lower_bound"].append(pred["lower_bound"])
            result["upper_bound"].append(pred["upper_bound"])
        
        return jsonify(result), 200
        
    except ValueError as ve:
        current_app.logger.error(f"Value error in get_latest_predictions: {str(ve)}")
        return jsonify({"status": "error", "message": f"Invalid parameter: {str(ve)}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting latest predictions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prediction_routes.route('/compare', methods=['GET'])
def compare_prediction_actual() -> Tuple[Dict[str, Any], int]:
    """
    Compare predicted energy production with actual production
    
    Query parameters:
        plant_id: The ID of the plant (required)
        device_sn: (Optional) The serial number of the device
        days: (Optional) Number of days to look back (default: 7)
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with comparison data and status code
    """
    try:
        # Get parameters from request
        plant_id = request.args.get('plant_id')
        mix_sn = request.args.get('device_sn')
        days = int(request.args.get('days', 7))
        
        if not plant_id:
            return jsonify({"status": "error", "message": "Plant ID is required"}), 400
        
        if days < 1 or days > 90:
            return jsonify({"status": "error", "message": "Days parameter must be between 1 and 90"}), 400
        
        # Get dates for the period
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Build query for actual energy data
        actual_query = """
            SELECT date, daily_energy 
            FROM energy_stats 
            WHERE plant_id = ? AND date >= ? AND date <= ?
        """
        params: List[Union[str, Any]] = [plant_id, start_date.isoformat(), end_date.isoformat()]
        
        if mix_sn:
            actual_query += " AND mix_sn = ?"
            params.append(mix_sn)
            
        actual_query += " ORDER BY date ASC"
        actual_data = db_connector.query(actual_query, tuple(params))
        
        # Build query for prediction data
        pred_query = """
            SELECT prediction_date, energy_predicted, lower_bound, upper_bound 
            FROM predictions 
            WHERE plant_id = ? AND prediction_date >= ? AND prediction_date <= ?
        """
        pred_params: List[Union[str, Any]] = [plant_id, start_date.isoformat(), end_date.isoformat()]
        
        if mix_sn:
            pred_query += " AND mix_sn = ?"
            pred_params.append(mix_sn)
            
        pred_query += " ORDER BY prediction_date ASC"
        pred_data = db_connector.query(pred_query, tuple(pred_params))
        
        # Prepare result data
        result = {
            "plant_id": plant_id,
            "device_sn": mix_sn,
            "dates": [],
            "actual": [],
            "predicted": [],
            "lower_bound": [],
            "upper_bound": [],
            "accuracy": []
        }
        
        # Create dictionaries of predictions and bounds by date for easy lookup
        predictions_by_date = {p["prediction_date"]: p["energy_predicted"] for p in pred_data}
        lower_bounds = {p["prediction_date"]: p["lower_bound"] for p in pred_data}
        upper_bounds = {p["prediction_date"]: p["upper_bound"] for p in pred_data}
        
        # Combine actual and predicted data
        for record in actual_data:
            date = record["date"]
            actual = record["daily_energy"]
            predicted = predictions_by_date.get(date)
            
            result["dates"].append(date)
            result["actual"].append(actual)
            result["predicted"].append(predicted)
            result["lower_bound"].append(lower_bounds.get(date))
            result["upper_bound"].append(upper_bounds.get(date))
            
            # Calculate accuracy if we have both values
            if predicted is not None and actual > 0:
                # Calculate accuracy: 1 - abs((actual - predicted) / actual) if actual > 0
                accuracy = 1 - min(1, abs((actual - predicted) / actual))
                result["accuracy"].append(round(accuracy, 2))
            else:
                result["accuracy"].append(None)
        
        # Calculate overall accuracy
        valid_accuracies = [acc for acc in result["accuracy"] if acc is not None]
        result["overall_accuracy"] = round(sum(valid_accuracies) / len(valid_accuracies), 2) if valid_accuracies else None
        
        # Add a trend indicator (increasing, decreasing, or stable)
        if len(valid_accuracies) >= 3:
            first_half = valid_accuracies[:len(valid_accuracies)//2]
            second_half = valid_accuracies[len(valid_accuracies)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            if second_avg > first_avg + 0.05:
                result["accuracy_trend"] = "increasing"
            elif second_avg < first_avg - 0.05:
                result["accuracy_trend"] = "decreasing"
            else:
                result["accuracy_trend"] = "stable"
        
        return jsonify(result), 200
        
    except ValueError as ve:
        current_app.logger.error(f"Value error in compare_prediction_actual: {str(ve)}")
        return jsonify({"status": "error", "message": f"Invalid parameter: {str(ve)}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error comparing predictions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prediction_routes.route('/accuracy-stats', methods=['GET'])
def get_prediction_accuracy_stats() -> Tuple[Dict[str, Any], int]:
    """
    Get statistics about the accuracy of predictions over time
    
    Query parameters:
        plant_id: The ID of the plant (required)
        device_sn: (Optional) The serial number of the device
        period: (Optional) Time period to analyze ('week', 'month', 'year', default: 'month')
    
    Returns:
        Tuple[Dict[str, Any], int]: JSON response with accuracy statistics and status code
    """
    try:
        # Get parameters from request
        plant_id = request.args.get('plant_id')
        mix_sn = request.args.get('device_sn')
        period = request.args.get('period', 'month')
        
        if not plant_id:
            return jsonify({"status": "error", "message": "Plant ID is required"}), 400
            
        # Determine date range based on period
        end_date = datetime.now().date()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            return jsonify({"status": "error", "message": "Invalid period. Use 'week', 'month', or 'year'"}), 400
        
        # First get all predictions within the period
        pred_query = """
            SELECT prediction_date, energy_predicted 
            FROM predictions 
            WHERE plant_id = ? AND prediction_date >= ? AND prediction_date <= ?
        """
        pred_params = [plant_id, start_date.isoformat(), end_date.isoformat()]
        
        if mix_sn:
            pred_query += " AND mix_sn = ?"
            pred_params.append(mix_sn)
            
        predictions = db_connector.query(pred_query, tuple(pred_params))
        
        # Then get actual energy data for the same dates
        actual_query = """
            SELECT date, daily_energy 
            FROM energy_stats 
            WHERE plant_id = ? AND date >= ? AND date <= ?
        """
        actual_params = [plant_id, start_date.isoformat(), end_date.isoformat()]
        
        if mix_sn:
            actual_query += " AND mix_sn = ?"
            actual_params.append(mix_sn)
            
        actual_data = db_connector.query(actual_query, tuple(actual_params))
        
        # Convert actual data to dictionary for easy lookup
        actual_by_date = {record['date']: record['daily_energy'] for record in actual_data}
        
        # Calculate accuracy stats
        accuracies = []
        for pred in predictions:
            date = pred['prediction_date']
            predicted = pred['energy_predicted']
            actual = actual_by_date.get(date)
            
            if actual is not None and actual > 0:
                accuracy = 1 - min(1, abs((actual - predicted) / actual))
                accuracies.append({
                    'date': date,
                    'accuracy': round(accuracy, 2),
                    'actual': actual,
                    'predicted': predicted
                })
        
        # Prepare statistics
        stats = {
            'plant_id': plant_id,
            'device_sn': mix_sn,
            'period': period,
            'total_predictions': len(predictions),
            'predictions_with_actual_data': len(accuracies),
            'accuracy_data': accuracies
        }
        
        if accuracies:
            accuracy_values = [item['accuracy'] for item in accuracies]
            stats['average_accuracy'] = round(sum(accuracy_values) / len(accuracy_values), 2)
            stats['min_accuracy'] = round(min(accuracy_values), 2)
            stats['max_accuracy'] = round(max(accuracy_values), 2)
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting prediction accuracy stats: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
