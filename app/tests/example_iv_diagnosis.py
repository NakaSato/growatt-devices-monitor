"""
Example usage of the I-V Curve Diagnosis system for PV modules.

This script demonstrates how to use the IVCurveDiagnosis class to:
1. Simulate I-V curves with various faults
2. Diagnose PV module health based on I-V curves
3. Generate visualizations and recommendations

The examples show both rule-based diagnosis (default when no training data is available)
and an optional ML-based classification approach.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add the parent directory to the path so we can import the app modules
script_dir = Path(__file__).parent
app_dir = script_dir.parent
sys.path.append(str(app_dir))

from app.ml.iv_curve_diagnosis import IVCurveDiagnosis

def demonstrate_iv_diagnosis():
    """
    Demonstrate the I-V curve diagnosis capabilities
    """
    print("I-V Curve Diagnosis for PV Modules - Example Usage")
    print("-" * 60)
    
    # Create a diagnosis system
    diagnosis = IVCurveDiagnosis()
    
    # List of fault types to simulate
    fault_types = [
        None,  # Normal operation (no fault)
        'partial_shading',
        'soiling',
        'series_resistance',
        'shunt_resistance',
        'degradation',
        'bypass_diode_failure'
    ]
    
    # Simulate and diagnose each fault type
    for fault in fault_types:
        print(f"\nSimulating {'normal operation' if fault is None else fault}...")
        
        # Simulate an I-V curve with the specified fault
        voltage, current = diagnosis.simulate_iv_curve(
            i_ph=10.0,        # Photogenerated current [A]
            i_0=1e-10,        # Diode saturation current [A]
            r_s=0.1,          # Series resistance [Ω]
            r_sh=100.0,       # Shunt resistance [Ω]
            v_oc_approx=40.0, # Approximate open circuit voltage [V]
            fault=fault       # Fault to inject
        )
        
        # Diagnose the simulated I-V curve
        result = diagnosis.diagnose(voltage, current, temperature=25.0)
        
        # Print the diagnosis results
        print(f"Diagnosed fault: {result['fault_type']} (confidence: {result['confidence']:.2f})")
        print(f"Health score: {result['health_score']:.1f}%")
        print(f"Key parameters:")
        print(f"  - I_sc: {result['parameters']['i_sc']:.2f} A")
        print(f"  - V_oc: {result['parameters']['v_oc']:.2f} V")
        print(f"  - P_max: {result['parameters']['p_max']:.2f} W")
        print(f"  - Fill Factor: {result['parameters']['fill_factor']:.4f}")
        
        print("Recommendations:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        # Plot and save the I-V curve
        save_dir = Path(script_dir, "iv_curve_examples")
        save_dir.mkdir(exist_ok=True)
        
        fault_name = 'normal' if fault is None else fault
        save_path = Path(save_dir, f"iv_curve_{fault_name}.png")
        
        # Plot with diagnosis information
        diagnosis.plot_iv_curve(
            voltage, 
            current, 
            diagnosis_result=result, 
            show=False,
            save_path=str(save_path)
        )
        
        print(f"I-V curve saved to {save_path}")
    
    print("\nDemonstration of ML-based training and diagnosis")
    print("-" * 60)
    
    # Generate training data from simulated curves
    training_data = []
    for fault in fault_types:
        if fault is None:
            fault = 'normal'  # Label as 'normal' when no fault
            
        # Generate 5 variations of each fault type
        for _ in range(5):
            # Add some variation to parameters
            i_ph = 9.5 + np.random.random()
            r_s = 0.08 + 0.04 * np.random.random()
            r_sh = 90.0 + 20.0 * np.random.random()
            
            # Simulate the I-V curve
            voltage, current = diagnosis.simulate_iv_curve(
                i_ph=i_ph, 
                r_s=r_s, 
                r_sh=r_sh, 
                fault=fault if fault != 'normal' else None
            )
            
            # Add to training data
            training_data.append({
                'voltage': voltage,
                'current': current,
                'fault_type': fault
            })
    
    # Train the ML model
    print(f"Training SVM model with {len(training_data)} samples...")
    success = diagnosis.train(training_data)
    
    if success:
        print("Training successful!")
        
        # Test the trained model with a new curve
        test_fault = 'partial_shading'
        print(f"\nTesting ML model with a new {test_fault} curve...")
        
        # Simulate a test curve
        voltage, current = diagnosis.simulate_iv_curve(
            i_ph=9.8,
            r_s=0.12,
            r_sh=95.0,
            fault=test_fault
        )
        
        # Diagnose using the trained model
        result = diagnosis.diagnose(voltage, current)
        
        print(f"Diagnosed fault: {result['fault_type']} (confidence: {result['confidence']:.2f})")
        print(f"Health score: {result['health_score']:.1f}%")
        
        # Plot the result
        save_path = Path(save_dir, "iv_curve_ml_prediction.png")
        diagnosis.plot_iv_curve(
            voltage, 
            current, 
            diagnosis_result=result, 
            show=False,
            save_path=str(save_path)
        )
        
        print(f"ML prediction I-V curve saved to {save_path}")
    else:
        print("Training failed. Check the logs for details.")

if __name__ == "__main__":
    demonstrate_iv_diagnosis()