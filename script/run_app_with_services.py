#!/usr/bin/env python3
"""
Script to start the Growatt application and verify background services are running.
This script:
1. Starts the Flask application in the background
2. Waits a few seconds for initialization
3. Runs the check_background_service script to verify services are running
4. Shows the application URL
"""

import os
import subprocess
import sys
import time
import logging
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
app_process = None

def cleanup(signum=None, frame=None):
    """Clean up resources and terminate the app process when the script exits."""
    global app_process
    
    if app_process:
        logger.info("Terminating Flask application...")
        try:
            app_process.terminate()
            app_process.wait(timeout=5)
            logger.info("Application terminated successfully")
        except subprocess.TimeoutExpired:
            logger.warning("Application did not terminate gracefully, forcing...")
            app_process.kill()
        except Exception as e:
            logger.error(f"Error terminating application: {e}")

def run_app_and_check_services():
    """Start the Flask app and check if background services are running."""
    global app_process
    
    try:
        # Register signal handlers for cleanup
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
        
        # Get host and port from environment or use defaults
        host = os.environ.get('FLASK_HOST', '127.0.0.1')
        port = int(os.environ.get('FLASK_PORT', '8000'))
        
        # Start the Flask application in the background
        logger.info("Starting Growatt Devices Monitor application...")
        main_script = os.path.join(root_dir, 'app', 'main.py')
        
        app_process = subprocess.Popen(
            [sys.executable, main_script, '--host', host, '--port', str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Create a thread to read and print the output
        def output_reader():
            for line in app_process.stdout:
                print(f"[APP] {line.strip()}")
        
        import threading
        output_thread = threading.Thread(target=output_reader, daemon=True)
        output_thread.start()
        
        # Wait for the application to start
        logger.info("Waiting for application to initialize (5 seconds)...")
        time.sleep(5)
        
        # Check if the application is still running
        if app_process.poll() is not None:
            logger.error(f"Application failed to start. Exit code: {app_process.returncode}")
            return False
        
        # Run the check_background_service script
        logger.info("Checking background service status...")
        check_script = os.path.join(script_dir, 'check_background_service.py')
        check_result = subprocess.run(
            [sys.executable, check_script],
            capture_output=True,
            text=True
        )
        
        # Print the output of the check script
        print("\n" + check_result.stdout)
        
        if check_result.returncode == 0:
            logger.info("Background services are running correctly")
        else:
            logger.warning("Background services are not running correctly")
            return False
        
        # Show application URL
        logger.info(f"Application is running at: http://{host}:{port}")
        logger.info("Press CTRL+C to stop the application")
        
        # Keep the script running until interrupted
        while app_process.poll() is None:
            time.sleep(1)
        
        return True
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        return True
    except Exception as e:
        logger.error(f"Error running application: {e}")
        return False
    finally:
        cleanup()

if __name__ == "__main__":
    success = run_app_and_check_services()
    sys.exit(0 if success else 1)