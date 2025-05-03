import numpy as np
import datetime
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn import svm
import logging
from typing import Dict, List, Tuple, Optional, Union

# Configure logger
logger = logging.getLogger(__name__)

class IVCurveDiagnosis:
    """
    Smart I-V Curve Diagnosis System for solar photovoltaic (PV) modules
    
    This class implements diagnosis capabilities to detect common faults in PV systems
    by analyzing current-voltage (I-V) curves using both physical models and machine learning.
    
    The system is based on the Shockley diode equation and can identify issues such as
    partial shading, soiling, degradation, and other common problems affecting solar panel
    performance.
    """
    
    def __init__(self, model_type: str = 'svm'):
        """
        Initialize the I-V curve diagnosis system
        
        Args:
            model_type (str): Type of ML model to use for diagnosis ('svm', 'random_forest', 'cnn')
        """
        self.model_type = model_type
        self.is_trained = False
        self.model = None
        self.scaler = StandardScaler()
        
        # Physical constants
        self.q = 1.602e-19  # Electron charge in C
        self.k = 1.381e-23  # Boltzmann constant in J/K
        
        # Default parameters
        self.n = 1.0  # Ideality factor
        self.T = 298.15  # Temperature in K (25°C)
        
        # Known fault signatures
        self.fault_signatures = {
            'normal': {'isc_ratio': 1.0, 'voc_ratio': 1.0, 'ff_ratio': 1.0, 'curvature': 'smooth'},
            'partial_shading': {'isc_ratio': 0.7, 'voc_ratio': 1.0, 'ff_ratio': 0.75, 'curvature': 'steps'},
            'soiling': {'isc_ratio': 0.8, 'voc_ratio': 1.0, 'ff_ratio': 0.9, 'curvature': 'smooth'},
            'degradation': {'isc_ratio': 0.9, 'voc_ratio': 0.9, 'ff_ratio': 0.85, 'curvature': 'smooth'},
            'series_resistance': {'isc_ratio': 1.0, 'voc_ratio': 1.0, 'ff_ratio': 0.8, 'curvature': 'flattened'},
            'shunt_resistance': {'isc_ratio': 1.0, 'voc_ratio': 1.0, 'ff_ratio': 0.7, 'curvature': 'drooping'},
            'bypass_diode_failure': {'isc_ratio': 1.0, 'voc_ratio': 0.67, 'ff_ratio': 0.5, 'curvature': 'notch'}
        }
    
    def shockley_equation(self, voltage, i_ph, i_0, r_s, r_sh) -> np.ndarray:
        """
        Compute current from the Shockley diode equation
        
        I = I_ph - I_0 * (exp((q(V + I*R_s))/(nkT)) - 1) - (V + I*R_s)/R_sh
        
        Args:
            voltage: Array of voltage values [V]
            i_ph: Photogenerated current [A]
            i_0: Diode reverse saturation current [A]
            r_s: Series resistance [Ω]
            r_sh: Shunt resistance [Ω]
            
        Returns:
            Array of current values [A]
        """
        # Solve the implicit equation iteratively
        current = np.zeros_like(voltage)
        for i, v in enumerate(voltage):
            # Initial guess of current (photocurrent)
            I = i_ph
            for _ in range(10):  # Usually converges in a few iterations
                # Update current based on Shockley equation
                v_diode = v + I * r_s
                I_diode = i_0 * (np.exp(self.q * v_diode / (self.n * self.k * self.T)) - 1)
                I_shunt = v_diode / r_sh
                I_new = i_ph - I_diode - I_shunt
                
                # Check for convergence
                if abs(I - I_new) < 1e-6:
                    break
                I = I_new
            
            current[i] = I
            
        return current
    
    def extract_iv_parameters(self, voltage, current) -> Dict[str, float]:
        """
        Extract key parameters from I-V curve data
        
        Args:
            voltage: Array of voltage measurements [V]
            current: Array of current measurements [A]
            
        Returns:
            Dictionary of extracted parameters
        """
        # Short circuit current (I at V=0)
        idx_isc = np.argmin(np.abs(voltage))
        i_sc = current[idx_isc]
        
        # Open circuit voltage (V at I=0)
        idx_voc = np.argmin(np.abs(current))
        v_oc = voltage[idx_voc]
        
        # Power calculation
        power = voltage * current
        
        # Maximum power point
        idx_mpp = np.argmax(power)
        p_max = power[idx_mpp]
        v_mpp = voltage[idx_mpp]
        i_mpp = current[idx_mpp]
        
        # Fill factor
        ff = p_max / (i_sc * v_oc) if (i_sc * v_oc) > 0 else 0
        
        # Calculate slope at low voltage (related to shunt resistance)
        low_v_indices = np.where(voltage < 0.2 * v_oc)[0]
        if len(low_v_indices) > 2:
            low_v = voltage[low_v_indices]
            low_i = current[low_v_indices]
            slope_low_v, _ = np.polyfit(low_v, low_i, 1)
        else:
            slope_low_v = 0
            
        # Calculate slope near Voc (related to series resistance)
        high_v_indices = np.where(voltage > 0.8 * v_oc)[0]
        if len(high_v_indices) > 2:
            high_v = voltage[high_v_indices]
            high_i = current[high_v_indices]
            slope_high_v, _ = np.polyfit(high_v, high_i, 1)
        else:
            slope_high_v = 0
        
        # Detect steps or kinks in curve (sign of partial shading)
        # Calculate second derivative to find inflection points
        if len(voltage) > 5:
            # Smooth the data first
            from scipy.signal import savgol_filter
            current_smooth = savgol_filter(current, min(5, len(current)), 2)
            # Approximate second derivative
            d2i_dv2 = np.gradient(np.gradient(current_smooth, voltage), voltage)
            # Count significant inflection points (where second derivative exceeds threshold)
            inflection_points = np.sum(np.abs(d2i_dv2) > 0.1 * np.max(np.abs(d2i_dv2)))
        else:
            inflection_points = 0
            
        return {
            'i_sc': i_sc,
            'v_oc': v_oc,
            'p_max': p_max,
            'v_mpp': v_mpp,
            'i_mpp': i_mpp,
            'fill_factor': ff,
            'slope_low_v': slope_low_v,
            'slope_high_v': slope_high_v,
            'inflection_points': inflection_points,
            'i_ratio': i_mpp / i_sc if i_sc > 0 else 0,
            'v_ratio': v_mpp / v_oc if v_oc > 0 else 0
        }
    
    def train(self, training_data: List[Dict]) -> bool:
        """
        Train the machine learning model for fault classification
        
        Args:
            training_data: List of dictionaries containing labeled I-V curve data
                Each dict should have 'voltage', 'current', and 'fault_type' keys
        
        Returns:
            bool: True if training was successful
        """
        if not training_data:
            logger.warning("No training data provided")
            return False
            
        logger.info(f"Training {self.model_type} model with {len(training_data)} samples")
        
        # Extract features from I-V curves
        X = []
        y = []
        
        for sample in training_data:
            voltage = np.array(sample['voltage'])
            current = np.array(sample['current'])
            fault = sample['fault_type']
            
            # Extract features from this I-V curve
            params = self.extract_iv_parameters(voltage, current)
            
            # Create feature vector [I_sc, V_oc, FF, I_mpp/I_sc, V_mpp/V_oc, slope_low_V]
            features = [
                params['i_sc'],
                params['v_oc'],
                params['fill_factor'],
                params['i_ratio'],
                params['v_ratio'],
                params['slope_low_v'],
                params['slope_high_v'],
                params['inflection_points']
            ]
            
            X.append(features)
            y.append(fault)
            
        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)
        
        if len(np.unique(y)) < 2:
            logger.warning("Training data contains only one class")
            return False
            
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model based on selected type
        if self.model_type == 'svm':
            self.model = svm.SVC(kernel='rbf', probability=True)
            self.model.fit(X_scaled, y)
        elif self.model_type == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=100)
            self.model.fit(X_scaled, y)
        elif self.model_type == 'cnn':
            # Placeholder for a CNN model - would require a different approach
            logger.warning("CNN model not yet implemented")
            return False
        else:
            logger.error(f"Unknown model type: {self.model_type}")
            return False
            
        self.is_trained = True
        return True
    
    def diagnose(self, voltage: np.ndarray, current: np.ndarray, 
                 temperature: float = 25.0) -> Dict[str, Union[str, float, Dict]]:
        """
        Diagnose PV module health based on I-V curve data
        
        Args:
            voltage: Array of voltage measurements [V]
            current: Array of current measurements [A]
            temperature: Module temperature in Celsius
        
        Returns:
            Dictionary with diagnosis results including:
            - fault_type: Classified fault type
            - confidence: Confidence level of the diagnosis
            - parameters: Extracted I-V parameters
            - health_score: Overall health score (0-100%)
            - recommendations: Recommendations for addressing the issue
        """
        # Adjust temperature from Celsius to Kelvin
        self.T = temperature + 273.15
        
        # Extract parameters from I-V curve
        params = self.extract_iv_parameters(voltage, current)
        
        # Fault diagnosis approach depends on whether we have a trained model
        if self.is_trained and self.model is not None:
            # Use ML model for classification
            features = [
                params['i_sc'],
                params['v_oc'],
                params['fill_factor'],
                params['i_ratio'],
                params['v_ratio'],
                params['slope_low_v'],
                params['slope_high_v'],
                params['inflection_points']
            ]
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Get prediction and probabilities
            fault_type = self.model.predict(features_scaled)[0]
            probs = self.model.predict_proba(features_scaled)[0]
            confidence = float(np.max(probs))
        else:
            # Use rule-based classification
            fault_type, confidence = self._rule_based_diagnosis(params)
        
        # Calculate health score (0-100%)
        health_score = self._calculate_health_score(params, fault_type)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(fault_type, params)
        
        return {
            'fault_type': fault_type,
            'confidence': confidence,
            'parameters': params,
            'health_score': health_score,
            'recommendations': recommendations
        }
    
    def _rule_based_diagnosis(self, params: Dict[str, float]) -> Tuple[str, float]:
        """
        Perform rule-based diagnosis when no ML model is available
        
        Args:
            params: Dictionary of extracted I-V parameters
            
        Returns:
            Tuple of (fault_type, confidence)
        """
        # Define conditions for each fault type
        ff = params['fill_factor']
        i_ratio = params['i_ratio']
        v_ratio = params['v_ratio']
        inflection_points = params['inflection_points']
        slope_low_v = params['slope_low_v']
        
        # Start with all possibilities
        fault_scores = {
            'normal': 0,
            'partial_shading': 0,
            'soiling': 0,
            'degradation': 0,
            'series_resistance': 0,
            'shunt_resistance': 0,
            'bypass_diode_failure': 0
        }
        
        # Check for partial shading (steps in curve)
        if inflection_points >= 2:
            fault_scores['partial_shading'] += 0.5
        
        # Check for low fill factor (general issue indicator)
        if ff < 0.5:
            fault_scores['degradation'] += 0.3
            fault_scores['series_resistance'] += 0.2
            fault_scores['bypass_diode_failure'] += 0.2
        elif ff < 0.65:
            fault_scores['degradation'] += 0.2
            fault_scores['series_resistance'] += 0.1
        elif ff > 0.75:
            fault_scores['normal'] += 0.4
        
        # Check I_mpp/I_sc ratio
        if i_ratio < 0.85:
            fault_scores['shunt_resistance'] += 0.3
        elif i_ratio > 0.9:
            fault_scores['normal'] += 0.2
            
        # Check V_mpp/V_oc ratio
        if v_ratio < 0.7:
            fault_scores['series_resistance'] += 0.3
        elif v_ratio > 0.8:
            fault_scores['normal'] += 0.2
            
        # Check for shunt resistance issues (slope at low voltage)
        if slope_low_v > -0.05:  # Shallow slope at low voltage
            fault_scores['shunt_resistance'] += 0.4
            
        # Find the most likely fault
        fault_type = max(fault_scores.items(), key=lambda x: x[1])[0]
        confidence = fault_scores[fault_type] / sum(fault_scores.values()) if sum(fault_scores.values()) > 0 else 0
        
        return fault_type, confidence
    
    def _calculate_health_score(self, params: Dict[str, float], fault_type: str) -> float:
        """
        Calculate overall health score based on I-V parameters and diagnosed fault
        
        Args:
            params: Dictionary of extracted I-V parameters
            fault_type: Diagnosed fault type
            
        Returns:
            Health score (0-100%)
        """
        # Base score from fill factor
        ff_score = params['fill_factor'] * 70  # Max 70 points from fill factor
        
        # Penalty based on fault type
        fault_penalties = {
            'normal': 0,
            'soiling': -10,
            'partial_shading': -15,
            'degradation': -30,
            'series_resistance': -25,
            'shunt_resistance': -20,
            'bypass_diode_failure': -40
        }
        
        penalty = fault_penalties.get(fault_type, -30)
        
        # Calculate health ratio based on I_mpp/I_sc and V_mpp/V_oc
        param_score = (params['i_ratio'] + params['v_ratio']) * 15  # Max 30 points
        
        # Combine scores
        health_score = ff_score + param_score + penalty
        
        # Clamp between 0 and 100
        return max(0, min(100, health_score))
    
    def _generate_recommendations(self, fault_type: str, params: Dict[str, float]) -> List[str]:
        """
        Generate maintenance recommendations based on diagnosed fault
        
        Args:
            fault_type: Diagnosed fault type
            params: Dictionary of extracted I-V parameters
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if fault_type == 'normal':
            recommendations.append("System operating normally. Continue regular maintenance.")
        
        elif fault_type == 'soiling':
            recommendations.append("Clean the PV modules to remove dirt, dust, or debris.")
            recommendations.append("Schedule regular cleaning based on local environmental conditions.")
            
        elif fault_type == 'partial_shading':
            recommendations.append("Check for shadows from nearby objects (trees, buildings, etc.).")
            recommendations.append("Consider trimming vegetation or adjusting module layout if possible.")
            recommendations.append("Verify bypass diode functionality.")
            
        elif fault_type == 'degradation':
            ff = params['fill_factor']
            if ff < 0.5:
                recommendations.append("Significant degradation detected. Consider module replacement.")
            else:
                recommendations.append("Module degradation detected. Monitor performance over time.")
            recommendations.append("Perform visual inspection for discoloration or delamination.")
            
        elif fault_type == 'series_resistance':
            recommendations.append("Check module connections and wiring for corrosion or loose connections.")
            recommendations.append("Inspect junction box for signs of damage or water ingress.")
            recommendations.append("Measure individual module resistances if possible.")
            
        elif fault_type == 'shunt_resistance':
            recommendations.append("Inspect for cell damage, hot spots, or micro-cracks using infrared camera.")
            recommendations.append("Check for potential-induced degradation (PID) if system has high voltage.")
            
        elif fault_type == 'bypass_diode_failure':
            recommendations.append("Test and replace faulty bypass diodes.")
            recommendations.append("Check junction box for signs of overheating.")
            recommendations.append("Consider full string I-V curve testing to isolate affected modules.")
            
        else:
            recommendations.append("Perform general system inspection to identify issues.")
        
        # Add general recommendations
        recommendations.append("Compare with previous I-V curve measurements to track changes over time.")
        
        return recommendations
    
    def simulate_iv_curve(self, 
                          i_ph: float = 10.0, 
                          i_0: float = 1e-10, 
                          r_s: float = 0.1, 
                          r_sh: float = 100.0,
                          v_oc_approx: float = 40.0,
                          fault: str = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate an I-V curve based on the single diode model with optional fault injection
        
        Args:
            i_ph: Photogenerated current [A]
            i_0: Diode reverse saturation current [A]
            r_s: Series resistance [Ω]
            r_sh: Shunt resistance [Ω]
            v_oc_approx: Approximate open circuit voltage [V]
            fault: Optional fault to inject ('partial_shading', 'soiling', etc.)
            
        Returns:
            Tuple of (voltage_array, current_array)
        """
        # Generate voltage array from 0 to Voc
        voltage = np.linspace(0, v_oc_approx * 1.1, 100)
        
        # Modify parameters based on fault type
        if fault == 'partial_shading':
            # For partial shading, divide the module into 3 segments
            # with one segment shaded (reduce i_ph for that segment)
            i_ph_values = [i_ph, i_ph, i_ph * 0.3]  # Last segment is shaded
            currents = []
            
            # Compute current for each segment
            for seg_i_ph in i_ph_values:
                seg_current = self.shockley_equation(voltage / 3, seg_i_ph, i_0, r_s, r_sh)
                currents.append(seg_current)
                
            # Apply bypass diode effect (minimum current between segments)
            current = np.minimum.reduce(currents)
            
        elif fault == 'soiling':
            # Soiling reduces photocurrent uniformly
            i_ph_reduced = i_ph * 0.8
            current = self.shockley_equation(voltage, i_ph_reduced, i_0, r_s, r_sh)
            
        elif fault == 'series_resistance':
            # Increased series resistance
            r_s_increased = r_s * 3
            current = self.shockley_equation(voltage, i_ph, i_0, r_s_increased, r_sh)
            
        elif fault == 'shunt_resistance':
            # Decreased shunt resistance
            r_sh_decreased = r_sh * 0.2
            current = self.shockley_equation(voltage, i_ph, i_0, r_s, r_sh_decreased)
            
        elif fault == 'degradation':
            # Degradation affects both photocurrent and saturation current
            i_ph_degraded = i_ph * 0.85
            i_0_degraded = i_0 * 2
            current = self.shockley_equation(voltage, i_ph_degraded, i_0_degraded, r_s, r_sh)
            
        elif fault == 'bypass_diode_failure':
            # Simulate voltage drop at the point where bypass diode would activate
            current = self.shockley_equation(voltage, i_ph, i_0, r_s, r_sh)
            # Modify curve to show voltage drop
            failure_idx = len(voltage) // 3
            current[failure_idx:] = current[failure_idx] * np.linspace(1, 0.3, len(voltage) - failure_idx)
            
        else:
            # Normal operation, no fault
            current = self.shockley_equation(voltage, i_ph, i_0, r_s, r_sh)
            
        return voltage, current
    
    def plot_iv_curve(self, voltage: np.ndarray, current: np.ndarray, 
                      diagnosis_result: Optional[Dict] = None, show: bool = True,
                      save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot I-V and P-V curves with diagnosis information
        
        Args:
            voltage: Array of voltage values [V]
            current: Array of current values [A]
            diagnosis_result: Optional diagnosis result dictionary
            show: Whether to display the plot
            save_path: Optional path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        # Calculate power
        power = voltage * current
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Plot I-V curve
        ax1.plot(voltage, current, 'b-', linewidth=2)
        ax1.set_xlabel('Voltage (V)')
        ax1.set_ylabel('Current (A)')
        ax1.set_title('I-V Curve')
        ax1.grid(True)
        
        # Plot P-V curve
        ax2.plot(voltage, power, 'r-', linewidth=2)
        ax2.set_xlabel('Voltage (V)')
        ax2.set_ylabel('Power (W)')
        ax2.set_title('P-V Curve')
        ax2.grid(True)
        
        # Add diagnosis information if available
        if diagnosis_result:
            params = diagnosis_result['parameters']
            fault = diagnosis_result['fault_type']
            health = diagnosis_result['health_score']
            
            # Mark key points on I-V curve
            ax1.plot(0, params['i_sc'], 'bo', markersize=8, label=f"Isc = {params['i_sc']:.2f} A")
            ax1.plot(params['v_oc'], 0, 'bo', markersize=8, label=f"Voc = {params['v_oc']:.2f} V")
            ax1.plot(params['v_mpp'], params['i_mpp'], 'ro', markersize=8, 
                    label=f"MPP: {params['v_mpp']:.2f} V, {params['i_mpp']:.2f} A")
            
            # Mark maximum power point on P-V curve
            ax2.plot(params['v_mpp'], params['p_max'], 'ro', markersize=8, 
                    label=f"Pmax = {params['p_max']:.2f} W")
            
            # Add text with diagnosis info
            plt.figtext(0.5, 0.01, 
                       f"Diagnosis: {fault.capitalize()} - Health Score: {health:.1f}% - FF: {params['fill_factor']:.3f}",
                       ha="center", fontsize=12, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
            
            ax1.legend(loc='lower left')
            ax2.legend(loc='lower right')
            
        plt.tight_layout()
        fig.subplots_adjust(bottom=0.15)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        if show:
            plt.show()
            
        return fig