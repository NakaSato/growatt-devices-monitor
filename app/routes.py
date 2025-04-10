import json
from flask import Blueprint, jsonify, render_template
from app.services import get_plants, get_plant_ids, get_devices_for_plant

# Create a Blueprint for routes
api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/', methods=['GET'])
def index():
    """
    Index route to render the homepage.
    """
    return render_template('index.html')

@api_blueprint.route('/plants', methods=['GET'])
def plants():
    """
    Get the list of plants associated with the logged-in user.
    """
    try:
        plants = get_plants()  # Call the function directly
        # return jsonify(json.loads(json.dumps(plants, ensure_ascii=False))), 200  # Ensure proper Unicode handling
        return render_template('plants.html', plants=plants)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api_blueprint.route('/devices', methods=['GET'])
def devices():
    """
    Render the devices page for a specific plant.
    """
    try:
        # Optionally, fetch the plant name or other details here
        return render_template('devices.html')
    except Exception as e:
        return render_template('404.html'), 404
    
@api_blueprint.route('/api/plants', methods=['GET'])
def api_plants():
    """
    Get the list of plants associated with the logged-in user.
    """
    try:
        plants = get_plants()  # Call the function directly
        return jsonify(json.loads(json.dumps(plants, ensure_ascii=False))), 200  # Ensure proper Unicode handling
        # return render_template('plants.html', plants=plants)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api_blueprint.route('/api/devices/', methods=['GET'])
def api_get_devices():
    """
    Get the list of devices for a specific plant ID.
    """
    try:
        plants = get_plants()  # Retrieve the list of plants
        plant_ids = [plant['id'] for plant in plants]  # Extract plant IDs
        devices = []  # Initialize an empty list to store devices

        for plant_id in plant_ids:
            plant_devices = get_devices_for_plant(plant_id)  # Fetch devices for each plant ID
            for device in plant_devices.get('datas', []):  # Safely access 'datas' key
                devices.append({
                    "alias": device['alias'],
                    "serial_number": device['sn'],
                    "plant_name": device['plantName'],
                    "total_energy": f"{device['eTotal']} kWh",
                    "last_update_time": device['lastUpdateTime'],
                    "status": 'Waiting' if device.get('status') == '0' else 'Online' if device.get('status') == '1' else 'Offline'
                })

        return jsonify(json.loads(json.dumps(devices, ensure_ascii=False))), 200  # Return the list of all devices as JSON

    except Exception as e:
        return jsonify({"error": str(e)}), 500
