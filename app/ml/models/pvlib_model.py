import pandas as pd
import numpy as np
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

class PVLibModel:
    def __init__(self, 
                 latitude, 
                 longitude, 
                 altitude,
                 module_parameters, 
                 inverter_parameters,
                 system_parameters,
                 temperature_model='sapm'):
        """
        Initialize PVLib model with system specifications.
        
        Args:
            latitude, longitude: Coordinates of the PV system
            altitude: Altitude in meters
            module_parameters: Dictionary with module parameters
            inverter_parameters: Dictionary with inverter parameters
            system_parameters: Dictionary with mounting and other system parameters
            temperature_model: Temperature model to use
        """
        self.location = Location(latitude, longitude, altitude=altitude)
        
        # Create the PV system
        self.system = PVSystem(
            module_parameters=module_parameters,
            inverter_parameters=inverter_parameters,
            temperature_model_parameters=TEMPERATURE_MODEL_PARAMETERS[temperature_model],
            **system_parameters
        )
        
        # Create the model chain
        self.model_chain = ModelChain(
            self.system, 
            self.location,
            aoi_model='physical',
            spectral_model='no_loss',
            temperature_model=temperature_model
        )
    
    def predict(self, weather_data):
        """
        Make predictions using PVLib and weather data.
        
        Args:
            weather_data: DataFrame with weather data columns 
                          (ghi, temp_air, wind_speed)
        
        Returns:
            DataFrame with PVLib predictions
        """
        # Prepare the weather data for PVLib
        weather = weather_data.copy()
        
        # Rename columns to match pvlib requirements if needed
        mapping = {
            'ghi': 'ghi',
            'temp_air': 'temp_air',
            'wind_speed': 'wind_speed'
        }
        
        weather = weather.rename(columns={k: v for k, v in mapping.items() if k in weather.columns})
        
        # Run the model
        self.model_chain.run_model(weather)
        
        # Get the DC and AC output
        dc_output = self.model_chain.dc
        ac_output = self.model_chain.ac
        
        results = pd.DataFrame({
            'pvlib_dc_power': dc_output.p_mp,
            'pvlib_ac_power': ac_output,
        }, index=weather.index)
        
        return results
    
    @staticmethod
    def estimate_parameters_from_data(df):
        """
        Estimate system parameters from historical data.
        This is a simple approach - in practice, more detailed 
        modeling would be required.
        
        Args:
            df: DataFrame with PV system data
            
        Returns:
            Dictionaries with estimated parameters
        """
        # Find the maximum voltage and current
        max_voltage = df['voltage'].max()
        max_current = df['current'].max()
        max_power = df['output_watt'].max()
        
        # Estimate module parameters (simplified)
        module_parameters = {
            'pdc0': max_power * 1.2,  # DC power rating with buffer
            'gamma_pdc': -0.004,  # typical power temperature coefficient
        }
        
        # Estimate inverter parameters (simplified)
        inverter_parameters = {
            'pdc0': max_power * 1.2,  # DC power rating
            'pac0': max_power,  # AC power rating
            'eta_inv_nom': 0.96,  # Nominal inverter efficiency
        }
        
        # Estimate system parameters
        system_parameters = {
            'surface_tilt': 20,  # Assume 20 degrees tilt (should be actual value)
            'surface_azimuth': 180,  # Assume south-facing (180° in pvlib convention)
            'albedo': 0.2,  # Typical albedo value
        }
        
        return module_parameters, inverter_parameters, system_parameters
