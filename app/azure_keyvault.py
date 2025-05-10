"""
Azure Key Vault integration for Growatt Devices Monitor

This module provides secure access to secrets stored in Azure Key Vault,
particularly useful for storing sensitive configuration like API keys and passwords.
"""

import logging
import os
from typing import Optional, Dict, Any

# Import Azure Key Vault libraries (will be installed with requirements update)
try:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient
    AZURE_KEYVAULT_AVAILABLE = True
except ImportError:
    AZURE_KEYVAULT_AVAILABLE = False

from app.config import Config

# Configure logger
logger = logging.getLogger(__name__)

class AzureKeyVault:
    """Azure Key Vault integration for secure secret management"""
    
    def __init__(self):
        """Initialize Azure Key Vault connection"""
        self.keyvault_url = os.environ.get('AZURE_KEYVAULT_URL', Config.AZURE_KEYVAULT_URL)
        self.use_managed_identity = os.environ.get('AZURE_MANAGED_IDENTITY_ENABLED', 
                                                 Config.AZURE_MANAGED_IDENTITY_ENABLED)
        self.enabled = bool(self.keyvault_url) and AZURE_KEYVAULT_AVAILABLE
        self.client = None
        
        if self.enabled:
            try:
                # Initialize the credential based on configuration
                if self.use_managed_identity:
                    credential = ManagedIdentityCredential()
                    logger.info("Using Managed Identity for Azure Key Vault authentication")
                else:
                    credential = DefaultAzureCredential()
                    logger.info("Using Default Azure Credential for Key Vault authentication")
                
                # Initialize the secret client
                self.client = SecretClient(vault_url=self.keyvault_url, credential=credential)
                
                logger.info(f"Azure Key Vault initialized with URL: {self.keyvault_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Azure Key Vault: {e}")
                self.enabled = False
        else:
            if not AZURE_KEYVAULT_AVAILABLE:
                logger.info("Azure Key Vault client not available - required packages not installed")
            else:
                logger.info("Azure Key Vault disabled - URL not configured")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get a secret from Azure Key Vault
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value or None if retrieval failed
        """
        if not self.enabled or not self.client:
            logger.warning("Azure Key Vault not enabled or properly initialized")
            return None
            
        try:
            # Get the secret
            secret = self.client.get_secret(secret_name)
            logger.debug(f"Retrieved secret {secret_name} from Key Vault")
            return secret.value
            
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_name} from Key Vault: {e}")
            return None
    
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Set a secret in Azure Key Vault
        
        Args:
            secret_name: Name of the secret to set
            secret_value: Value of the secret
            
        Returns:
            True if secret was set successfully, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Azure Key Vault not enabled or properly initialized")
            return False
            
        try:
            # Set the secret
            self.client.set_secret(secret_name, secret_value)
            logger.info(f"Set secret {secret_name} in Key Vault")
            return True
            
        except Exception as e:
            logger.error(f"Error setting secret {secret_name} in Key Vault: {e}")
            return False
    
    def load_secrets_to_environment(self, secret_names: list) -> bool:
        """
        Load specified secrets from Key Vault into environment variables
        
        Args:
            secret_names: List of secret names to load
            
        Returns:
            True if all secrets were loaded, False if any failed
        """
        if not self.enabled or not self.client:
            logger.warning("Azure Key Vault not enabled or properly initialized")
            return False
            
        success = True
        for secret_name in secret_names:
            try:
                # Get the secret
                secret_value = self.get_secret(secret_name)
                
                if secret_value:
                    # Set as environment variable
                    os.environ[secret_name] = secret_value
                else:
                    success = False
                    
            except Exception as e:
                logger.error(f"Error loading secret {secret_name} to environment: {e}")
                success = False
                
        return success
    
    def load_all_secrets_to_environment(self) -> Dict[str, str]:
        """
        Load all secrets from Key Vault into environment variables
        
        Returns:
            Dictionary of secret names that were loaded
        """
        if not self.enabled or not self.client:
            logger.warning("Azure Key Vault not enabled or properly initialized")
            return {}
            
        loaded_secrets = {}
        try:
            # List all secrets
            secret_properties = self.client.list_properties_of_secrets()
            
            # Load each secret
            for secret_property in secret_properties:
                secret_name = secret_property.name
                secret_value = self.get_secret(secret_name)
                
                if secret_value:
                    # Set as environment variable
                    os.environ[secret_name] = secret_value
                    loaded_secrets[secret_name] = "***HIDDEN***"
                
            logger.info(f"Loaded {len(loaded_secrets)} secrets to environment variables")
            return loaded_secrets
            
        except Exception as e:
            logger.error(f"Error loading all secrets to environment: {e}")
            return loaded_secrets

# Create a singleton instance
azure_keyvault = AzureKeyVault()
