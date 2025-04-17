import pandas as pd
import numpy as np
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS
from pvlib.irradiance import disc, dirint

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
        
        # Get temperature model parameters
        module_type = system_parameters.pop('module_type', 'glass_polymer')
        racking_model = system_parameters.pop('racking_model', 'open_rack')
        
        # Extract temperature model parameters from the correct dictionary
        temp_model_params = TEMPERATURE_MODEL_PARAMETERS[temperature_model].get(
            f'{module_type}_{racking_model}',
            TEMPERATURE_MODEL_PARAMETERS[temperature_model]['open_rack_glass_glass']
        )
        
        # Create the PV system
        self.system = PVSystem(
            module_parameters=module_parameters,
            inverter_parameters=inverter_parameters,
            temperature_model_parameters=temp_model_params,
            **system_parameters
        )
        
        # Create the model chain with a complete irradiance model
        self.model_chain = ModelChain(
            self.system, 
            self.location,
            aoi_model='physical',
            spectral_model='no_loss',
            temperature_model=temperature_model,
            dc_model='desoto',
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
        
        # Calculate solar position for the given timestamps and location
        solar_position = self.location.get_solarposition(weather.index)
        
        # Calculate DNI from GHI using the DISC model
        disc_result = disc(weather['ghi'], 
                           solar_position['zenith'], 
                           solar_position.index)
        weather['dni'] = disc_result['dni']
        
        # Calculate DHI from GHI and DNI
        weather['dhi'] = weather['ghi'] - weather['dni'] * np.cos(np.radians(solar_position['zenith']))
        
        # Ensure no negative values
        weather['dhi'] = weather['dhi'].clip(lower=0)
        weather['dni'] = weather['dni'].clip(lower=0)
        
        # Run the model with the complete weather data
        try:
            self.model_chain.run_model(weather)
            
            # Get the DC and AC output using the correct attributes
            # In newer versions of pvlib, dc is accessed as dc.p_mp
            if hasattr(self.model_chain, 'dc'):
                # Old way
                dc_output = self.model_chain.dc.p_mp if hasattr(self.model_chain.dc, 'p_mp') else self.model_chain.dc
            else:
                # New way - ModelChain might store results in different attributes
                dc_output = self.model_chain.results.dc.p_mp if hasattr(self.model_chain, 'results') else None
            
            # Similarly for AC output
            if hasattr(self.model_chain, 'ac'):
                ac_output = self.model_chain.ac
            else:
                ac_output = self.model_chain.results.ac if hasattr(self.model_chain, 'results') else None
            
            # If we still don't have values, use a fallback approach
            if dc_output is None or ac_output is None:
                print("Warning: Could not find DC/AC outputs in expected attributes. Using fallback.")
                # Attempt to extract values from whatever is available
                dc_output = np.zeros(len(weather))
                ac_output = np.zeros(len(weather))
            
            results = pd.DataFrame({
                'pvlib_dc_power': dc_output,
                'pvlib_ac_power': ac_output,
            }, index=weather.index)
            
            return results
        except Exception as e:
            print(f"Error in PVLib prediction: {e}")
            # Return empty dataframe with expected columns
            return pd.DataFrame({
                'pvlib_dc_power': np.zeros(len(weather)),
                'pvlib_ac_power': np.zeros(len(weather)),
            }, index=weather.index)
    
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
        
        # Estimate module parameters including required parameters for desoto model
        module_parameters = {
            'pdc0': max_power * 1.2,  # DC power rating with buffer
            'gamma_pdc': -0.004,  # typical power temperature coefficient
            'module_type': 'glass_polymer',  # Add module type for temperature model
            
            # Required parameters for the desoto model
            'I_L_ref': max_current * 1.1,  # Light current at reference condition
            'I_o_ref': 1e-9,  # Dark current at reference condition
            'R_s': 0.5,  # Series resistance
            'R_sh_ref': 500,  # Shunt resistance at reference condition
            'a_ref': 2.5,  # Modified ideality factor at reference condition
            'alpha_sc': 0.001,  # Short-circuit current temperature coefficient
            
            # Additional parameters that might be useful
            'EgRef': 1.121,  # Energy bandgap at reference temperature
            'dEgdT': -0.0002677,  # Temperature dependency of bandgap
            'cells_in_series': 72,  # Typical number of cells for 5kW system
            'temp_ref': 25  # Reference temperature
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
            'racking_model': 'open_rack',  # Add racking model for temperature model
        }
        
        return module_parameters, inverter_parameters, system_parameters
