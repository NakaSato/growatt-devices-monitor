"""
Azure Application Insights Integration for Growatt Devices Monitor

This module provides integration with Azure Application Insights for application monitoring,
performance tracking, and diagnostics in the Azure environment.
"""

import logging
import os
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from app.config import Config

# Configure logger
logger = logging.getLogger(__name__)

class AzureMonitoring:
    """Azure Application Insights integration for application monitoring"""
    
    def __init__(self):
        """Initialize Azure monitoring with Application Insights"""
        self.instrumentation_key = os.environ.get('APPINSIGHTS_INSTRUMENTATIONKEY', 
                                                 Config.APPINSIGHTS_INSTRUMENTATIONKEY)
        self.enabled = bool(self.instrumentation_key) and os.environ.get('AZURE_MONITORING_ENABLED', 
                                                                        Config.AZURE_MONITORING_ENABLED)
        self.middleware = None
        self.tracer = None
        
        if self.enabled:
            # Configure the tracer for custom events
            self.tracer = Tracer(
                exporter=AzureExporter(connection_string=f'InstrumentationKey={self.instrumentation_key}'),
                sampler=ProbabilitySampler(1.0)  # Sample 100% of requests
            )
            
            # Configure logging to Application Insights
            self._setup_logging()
            
            logger.info("Azure Application Insights monitoring initialized")
        else:
            logger.info("Azure monitoring disabled - Application Insights instrumentation key not configured")
    
    def init_app(self, app):
        """
        Initialize Flask application with Azure monitoring middleware
        
        Args:
            app: Flask application instance
        """
        if not self.enabled or not app:
            return
            
        # Initialize Flask middleware for request tracking
        self.middleware = FlaskMiddleware(
            app,
            exporter=AzureExporter(connection_string=f'InstrumentationKey={self.instrumentation_key}'),
            sampler=ProbabilitySampler(1.0)
        )
        
        logger.info("Azure Application Insights middleware attached to Flask app")
        
    def _setup_logging(self):
        """Configure logging to send logs to Application Insights"""
        if not self.enabled:
            return
            
        # Create a handler for Azure
        azure_handler = AzureLogHandler(connection_string=f'InstrumentationKey={self.instrumentation_key}')
        
        # Set the minimum log level
        azure_handler.setLevel(logging.WARNING)  # Only send warnings and errors to App Insights
        
        # Add the handler to the root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(azure_handler)
        
    def track_event(self, name, properties=None, measurements=None):
        """
        Track a custom event in Application Insights
        
        Args:
            name: Name of the event
            properties: Dictionary of custom properties
            measurements: Dictionary of custom measurements
        """
        if not self.enabled or not self.tracer:
            return
            
        with self.tracer.span(name) as span:
            if properties:
                for key, value in properties.items():
                    span.add_attribute(key, value)
            
            # Log the event for debugging
            logger.debug(f"Tracked event: {name} with properties: {properties} and measurements: {measurements}")
    
    def track_exception(self, exception, properties=None):
        """
        Track an exception in Application Insights
        
        Args:
            exception: The exception to track
            properties: Dictionary of custom properties
        """
        if not self.enabled or not self.tracer:
            return
            
        # Log the exception
        logger.exception(f"Exception tracked: {str(exception)}")
        
        # Track in Application Insights
        with self.tracer.span("exception") as span:
            span.add_attribute("exception.type", exception.__class__.__name__)
            span.add_attribute("exception.message", str(exception))
            
            if properties:
                for key, value in properties.items():
                    span.add_attribute(key, value)

# Create a singleton instance
azure_monitoring = AzureMonitoring()
