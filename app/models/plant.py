from datetime import datetime

class Plant:
    """Model representing a solar plant"""
    
    def __init__(self, id, name, status, latitude, longitude, capacity, 
                 current_output=0, today_energy=0, peak_output=0, 
                 install_date=None, location=None):
        self.id = id
        self.name = name
        self.status = status  # 'active', 'warning', 'error', 'offline', 'maintenance'
        self.latitude = latitude
        self.longitude = longitude
        self.capacity = capacity  # in kW
        self.current_output = current_output  # current power output in kW
        self.today_energy = today_energy  # energy generated today in kWh
        self.peak_output = peak_output  # peak power output today in kW
        self.install_date = install_date  # installation date
        self.location = location  # text description of location
        
    @classmethod
    def from_dict(cls, data):
        """Create a Plant instance from a dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            status=data.get('status', 'offline'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            capacity=data.get('capacity', 0),
            current_output=data.get('current_output', 0),
            today_energy=data.get('today_energy', 0),
            peak_output=data.get('peak_output', 0),
            install_date=datetime.strptime(data.get('install_date'), "%Y-%m-%d") 
                if data.get('install_date') else None,
            location=data.get('location')
        )
    
    def to_dict(self):
        """Convert Plant object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'capacity': self.capacity,
            'current_output': self.current_output,
            'today_energy': self.today_energy,
            'peak_output': self.peak_output,
            'install_date': self.install_date.strftime("%Y-%m-%d") if self.install_date else None,
            'location': self.location
        }
