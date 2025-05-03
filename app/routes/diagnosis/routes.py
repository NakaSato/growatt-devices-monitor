from flask import Blueprint, jsonify, request, send_file
import logging
import os
import tempfile
import json
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment
import matplotlib.pyplot as plt
import numpy as np

# Import the I-V curve diagnosis system
from app.ml.iv_curve_diagnosis import IVCurveDiagnosis
from app.views.templates import render_diagnosis

# Create blueprint
diagnosis_routes = Blueprint('diagnosis_routes', __name__)

# Initialize the I-V curve diagnosis system
iv_diagnosis = IVCurveDiagnosis()

@diagnosis_routes.route('/diagnosis', methods=['GET'])
def show_diagnosis_page():
    """
    Render the IV curve diagnosis page
    """
    return render_diagnosis()

@diagnosis_routes.route('/api/diagnosis/iv-curve', methods=['POST'])
def diagnose_iv_curve():
    """
    Diagnose issues from IV curve data
    """
    try:
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

@diagnosis_routes.route('/api/diagnosis/iv-curve/plot', methods=['POST'])
def plot_iv_curve():
    """
    Generate a plot of the IV curve with diagnosis markers
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Extract IV curve data
        voltage = data.get('voltage')
        current = data.get('current')
        
        if not voltage or not current:
            return jsonify({'error': 'Voltage and current arrays are required'}), 400
            
        if len(voltage) != len(current):
            return jsonify({'error': 'Voltage and current arrays must have the same length'}), 400
        
        # Convert to numpy arrays
        voltage = np.array(voltage)
        current = np.array(current)
        
        # Create a temporary file for the plot
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            # If diagnosis is requested, get diagnosis result
            diagnosis_result = None
            if data.get('with_diagnosis', True):
                temperature = data.get('temperature', 25.0)
                diagnosis_result = iv_diagnosis.diagnose(voltage, current, temperature)
            
            # Generate plot using the IVCurveDiagnosis class method
            fig = iv_diagnosis.plot_iv_curve(
                voltage, 
                current, 
                diagnosis_result=diagnosis_result, 
                show=False
            )
            
            fig.savefig(temp_file.name, dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            # Send the file to the client
            return send_file(temp_file.name, mimetype='image/png', 
                           as_attachment=True, download_name='iv_curve_analysis.png')
        
    except Exception as e:
        logging.error(f"Error in I-V curve plot API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@diagnosis_routes.route('/api/diagnosis/simulate-iv-curve', methods=['GET'])
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

@diagnosis_routes.route('/api/diagnosis/train-model', methods=['POST'])
def train_diagnosis_model():
    """
    Train or update the IV curve diagnosis model with new data
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

@diagnosis_routes.route('/api/diagnosis/iv-curve-report', methods=['POST'])
def generate_iv_curve_report():
    """
    Generate a comprehensive report for PV module health based on I-V curve data
    
    Expected JSON payload:
    {
        "voltage": [v1, v2, ...],  // Array of voltage measurements [V]
        "current": [i1, i2, ...],  // Array of current measurements [A]
        "temperature": 25.0,       // Module temperature in Celsius (optional)
        "module_id": "abc123",     // Module identifier (optional)
        "plant_name": "Plant 1",   // Plant name (optional)
        "report_format": "pdf"     // Report format: 'pdf', 'json', or 'html' (optional, default: 'pdf')
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
        plant_name = data.get('plant_name', 'Unknown Plant')
        report_format = data.get('report_format', 'pdf').lower()
        
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
        diagnosis_result['plant_name'] = plant_name
        
        # Generate appropriate report based on format
        if report_format == 'json':
            # Return JSON report directly
            return jsonify({
                'status': 'success',
                'report_type': 'json',
                'data': diagnosis_result
            })
            
        elif report_format in ['pdf', 'html']:
            # Create a temporary directory for report files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Generate plot and save to the temp directory
                fig = iv_diagnosis.plot_iv_curve(
                    voltage, 
                    current, 
                    diagnosis_result=diagnosis_result, 
                    show=False
                )
                
                # Create file paths
                temp_dir_path = Path(temp_dir)
                plot_path = temp_dir_path / 'iv_curve_plot.png'
                report_path = temp_dir_path / f'iv_curve_report.{report_format}'
                
                # Save the plot
                fig.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                # Generate report content
                report_content = _generate_report_content(
                    diagnosis_result, 
                    module_id, 
                    plant_name, 
                    temperature,
                    plot_path
                )
                
                if report_format == 'pdf':
                    # Generate PDF using the report content
                    _generate_pdf_report(report_content, report_path)
                    
                    # Return the PDF file
                    return send_file(
                        report_path, 
                        mimetype='application/pdf',
                        as_attachment=True, 
                        download_name=f'iv_curve_report_{module_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
                    )
                    
                else:  # HTML
                    # Save HTML report
                    with open(report_path, 'w') as f:
                        f.write(report_content)
                        
                    # Return the HTML file
                    return send_file(
                        report_path, 
                        mimetype='text/html',
                        as_attachment=True, 
                        download_name=f'iv_curve_report_{module_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
                    )
        else:
            return jsonify({'error': f'Unsupported report format: {report_format}'}), 400
            
    except Exception as e:
        logging.error(f"Error generating I-V curve report: {str(e)}")
        return jsonify({'error': str(e)}), 500

def _generate_report_content(diagnosis_result, module_id, plant_name, temperature, plot_path):
    """Generate HTML content for the report"""
    # Format the timestamp
    timestamp = datetime.fromisoformat(diagnosis_result['timestamp'])
    formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    # Get parameters
    params = diagnosis_result['parameters']
    
    # Format recommendations as HTML list
    recommendations_html = ''.join([f'<li>{rec}</li>' for rec in diagnosis_result['recommendations']])
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IV Curve Diagnosis Report - {module_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
            .report-header {{ text-align: center; margin-bottom: 30px; }}
            .report-title {{ color: #2c3e50; margin-bottom: 10px; }}
            .report-date {{ color: #7f8c8d; font-size: 0.9em; }}
            .section {{ margin-bottom: 25px; }}
            .section-title {{ color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .summary-box {{ background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin-bottom: 20px; }}
            .fault-type {{ font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }}
            .health-score {{ font-size: 1.2em; }}
            .parameters-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .parameters-table th, .parameters-table td {{ padding: 12px 15px; border-bottom: 1px solid #ddd; text-align: left; }}
            .parameters-table th {{ background-color: #f2f2f2; }}
            .recommendations {{ background-color: #f0f7fb; border-left: 4px solid #5bc0de; padding: 15px; }}
            .plot-container {{ text-align: center; margin: 30px 0; }}
            .plot-image {{ max-width: 100%; height: auto; }}
            .footer {{ text-align: center; margin-top: 40px; font-size: 0.8em; color: #7f8c8d; }}
            
            /* Health score color coding */
            .health-excellent {{ color: #27ae60; }}
            .health-good {{ color: #2ecc71; }}
            .health-fair {{ color: #f39c12; }}
            .health-poor {{ color: #e74c3c; }}
            .health-critical {{ color: #c0392b; }}
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1 class="report-title">IV Curve Diagnosis Report</h1>
            <div class="report-date">Generated on: {formatted_time}</div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Module Information</h2>
            <p><strong>Module ID:</strong> {module_id}</p>
            <p><strong>Plant Name:</strong> {plant_name}</p>
            <p><strong>Temperature:</strong> {temperature}°C</p>
        </div>
        
        <div class="section">
            <h2 class="section-title">Diagnosis Summary</h2>
            <div class="summary-box">
                <div class="fault-type">Fault Type: {diagnosis_result['fault_type'].replace('_', ' ').title()}</div>
                <div class="health-score">
                    Health Score: <span class="{_get_health_score_class(diagnosis_result['health_score'])}">{diagnosis_result['health_score']:.1f}%</span>
                </div>
                <p><strong>Confidence:</strong> {diagnosis_result['confidence']*100:.1f}%</p>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">IV Curve Plot</h2>
            <div class="plot-container">
                <img src="data:image/png;base64,{_encode_image(plot_path)}" class="plot-image" alt="IV Curve Plot">
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Key Parameters</h2>
            <table class="parameters-table">
                <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Short Circuit Current (Isc)</td>
                    <td>{params['i_sc']:.3f} A</td>
                </tr>
                <tr>
                    <td>Open Circuit Voltage (Voc)</td>
                    <td>{params['v_oc']:.3f} V</td>
                </tr>
                <tr>
                    <td>Maximum Power (Pmax)</td>
                    <td>{params['p_max']:.3f} W</td>
                </tr>
                <tr>
                    <td>Maximum Power Point Voltage (Vmpp)</td>
                    <td>{params['v_mpp']:.3f} V</td>
                </tr>
                <tr>
                    <td>Maximum Power Point Current (Impp)</td>
                    <td>{params['i_mpp']:.3f} A</td>
                </tr>
                <tr>
                    <td>Fill Factor</td>
                    <td>{params['fill_factor']:.3f}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">Recommendations</h2>
            <div class="recommendations">
                <ul>
                    {recommendations_html}
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Growatt Devices Monitor - IV Curve Diagnosis System</p>
        </div>
    </body>
    </html>
    """
    
    return html_content

def _get_health_score_class(health_score):
    """Determine CSS class based on health score"""
    if health_score >= 90:
        return "health-excellent"
    elif health_score >= 75:
        return "health-good"
    elif health_score >= 50:
        return "health-fair"
    elif health_score >= 25:
        return "health-poor"
    else:
        return "health-critical"

def _encode_image(image_path):
    """Encode image to base64 for embedding in HTML"""
    import base64
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def _generate_pdf_report(html_content, output_path):
    """Generate PDF report from HTML content"""
    # Import here to avoid unnecessary dependencies if not generating PDF
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
    except ImportError:
        # Fallback to alternative PDF generation if WeasyPrint not available
        try:
            import pdfkit
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': 'UTF-8',
            }
            pdfkit.from_string(html_content, output_path, options=options)
        except ImportError:
            # Last resort - create a plain text version and save to PDF
            import fpdf
            from html.parser import HTMLParser
            
            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                
                def handle_data(self, data):
                    self.text.append(data.strip())
                
                def get_text(self):
                    return '\n'.join(t for t in self.text if t)
            
            # Extract text from HTML
            extractor = HTMLTextExtractor()
            extractor.feed(html_content)
            text_content = extractor.get_text()
            
            # Create PDF with text content
            pdf = fpdf.FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Split text into lines and add to PDF
            for line in text_content.split('\n'):
                pdf.multi_cell(0, 10, line)
                
            pdf.output(output_path)