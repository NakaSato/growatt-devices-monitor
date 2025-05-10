"""
Azure Blob Storage integration for Growatt Devices Monitor

This module provides functionality to store files in Azure Blob Storage,
particularly useful for storing report PDFs and data exports from the application.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Union, BinaryIO

# Import Azure Storage libraries (will be installed with requirements update)
try:
    from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient, ContentSettings
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
    AZURE_STORAGE_AVAILABLE = True
except ImportError:
    AZURE_STORAGE_AVAILABLE = False

from app.config import Config

# Configure logger
logger = logging.getLogger(__name__)

class AzureBlobStorage:
    """Azure Blob Storage integration for file storage"""
    
    def __init__(self):
        """Initialize Azure Blob Storage connection"""
        self.connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', 
                                              Config.AZURE_STORAGE_CONNECTION_STRING)
        self.container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 
                                           Config.AZURE_STORAGE_CONTAINER_NAME)
        self.enabled = bool(self.connection_string) and AZURE_STORAGE_AVAILABLE
        self.service_client = None
        self.container_client = None
        
        if self.enabled:
            try:
                # Initialize the connection to Azure Blob Storage
                self.service_client = BlobServiceClient.from_connection_string(self.connection_string)
                
                # Get or create container
                self._ensure_container_exists()
                
                logger.info(f"Azure Blob Storage initialized with container: {self.container_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Azure Blob Storage: {e}")
                self.enabled = False
        else:
            if not AZURE_STORAGE_AVAILABLE:
                logger.info("Azure Blob Storage client not available - required packages not installed")
            else:
                logger.info("Azure Blob Storage disabled - connection string not configured")
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        if not self.enabled or not self.service_client:
            return
            
        try:
            # Try to get container client
            self.container_client = self.service_client.get_container_client(self.container_name)
            
            # Check if container exists by listing blobs (this will raise an exception if not exists)
            self.container_client.list_blobs(max_results=1)
            logger.debug(f"Container '{self.container_name}' already exists")
        except ResourceNotFoundError:
            # Container doesn't exist, create it
            logger.info(f"Creating container '{self.container_name}'")
            self.container_client = self.service_client.create_container(self.container_name)
        except Exception as e:
            logger.error(f"Error checking/creating container: {e}")
            raise
    
    def upload_file(self, file_path: Union[str, Path], 
                   blob_path: Optional[str] = None, 
                   content_type: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Azure Blob Storage
        
        Args:
            file_path: Local path to the file
            blob_path: Optional path within the blob container (defaults to filename)
            content_type: Optional content type (MIME type)
            
        Returns:
            URL of the uploaded blob or None if upload failed
        """
        if not self.enabled or not self.container_client:
            logger.warning("Azure Blob Storage not enabled or properly initialized")
            return None
            
        try:
            # Convert to Path object for easier handling
            file_path = Path(file_path)
            
            # If blob_path is not specified, use the file name
            if not blob_path:
                blob_path = file_path.name
            
            # Determine content type based on file extension if not provided
            if not content_type:
                if file_path.suffix.lower() == '.pdf':
                    content_type = 'application/pdf'
                elif file_path.suffix.lower() == '.csv':
                    content_type = 'text/csv'
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif file_path.suffix.lower() == '.json':
                    content_type = 'application/json'
                else:
                    content_type = 'application/octet-stream'
            
            # Create blob client
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Set content settings
            content_settings = ContentSettings(content_type=content_type)
            
            # Upload file
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
            
            logger.info(f"File {file_path} uploaded to blob storage as {blob_path}")
            
            # Return the URL of the uploaded blob
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Error uploading file to Azure Blob Storage: {e}")
            return None
    
    def upload_bytes(self, data: bytes, 
                    blob_path: str, 
                    content_type: Optional[str] = None) -> Optional[str]:
        """
        Upload bytes to Azure Blob Storage
        
        Args:
            data: Bytes to upload
            blob_path: Path within the blob container
            content_type: Optional content type (MIME type)
            
        Returns:
            URL of the uploaded blob or None if upload failed
        """
        if not self.enabled or not self.container_client:
            logger.warning("Azure Blob Storage not enabled or properly initialized")
            return None
        
        try:
            # Create blob client
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Set content settings if provided
            content_settings = ContentSettings(content_type=content_type) if content_type else None
            
            # Upload data
            blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
            
            logger.info(f"Bytes uploaded to blob storage as {blob_path}")
            
            # Return the URL of the uploaded blob
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Error uploading bytes to Azure Blob Storage: {e}")
            return None
    
    def download_file(self, blob_path: str, local_path: Union[str, Path]) -> bool:
        """
        Download a file from Azure Blob Storage
        
        Args:
            blob_path: Path of the blob within the container
            local_path: Local path where to save the file
            
        Returns:
            True if download succeeded, False otherwise
        """
        if not self.enabled or not self.container_client:
            logger.warning("Azure Blob Storage not enabled or properly initialized")
            return False
            
        try:
            # Create blob client
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Ensure directory exists
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the blob
            with open(local_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
                
            logger.info(f"Downloaded blob {blob_path} to {local_path}")
            return True
            
        except ResourceNotFoundError:
            logger.error(f"Blob {blob_path} not found in container {self.container_name}")
            return False
        except Exception as e:
            logger.error(f"Error downloading blob {blob_path}: {e}")
            return False
    
    def generate_download_url(self, blob_path: str, expiry_hours: int = 24) -> Optional[str]:
        """
        Generate a temporary download URL with SAS token
        
        Args:
            blob_path: Path of the blob within the container
            expiry_hours: Number of hours until the URL expires
            
        Returns:
            Temporary URL with SAS token or None if failed
        """
        if not self.enabled or not self.service_client:
            logger.warning("Azure Blob Storage not enabled or properly initialized")
            return None
            
        try:
            # Create blob client
            account_name = self.service_client.account_name
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Check if blob exists
            try:
                blob_client.get_blob_properties()
            except ResourceNotFoundError:
                logger.error(f"Blob {blob_path} not found in container {self.container_name}")
                return None
            
            # Calculate expiry time
            expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
            
            # Create SAS token with read permission
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_path,
                account_key=self.service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry
            )
            
            # Create the URL with SAS token
            sas_url = f"{blob_client.url}?{sas_token}"
            
            logger.info(f"Generated temporary download URL for {blob_path} (expires in {expiry_hours} hours)")
            return sas_url
            
        except Exception as e:
            logger.error(f"Error generating download URL for {blob_path}: {e}")
            return None
    
    def list_blobs(self, prefix: Optional[str] = None) -> List[Dict]:
        """
        List blobs in the container
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of dictionaries with blob information
        """
        if not self.enabled or not self.container_client:
            logger.warning("Azure Blob Storage not enabled or properly initialized")
            return []
            
        try:
            # List blobs with the given prefix
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            # Convert to list of dicts with relevant info
            result = []
            for blob in blobs:
                result.append({
                    'name': blob.name,
                    'size': blob.size,
                    'created_on': blob.creation_time,
                    'last_modified': blob.last_modified,
                    'content_type': blob.content_settings.content_type
                })
                
            return result
            
        except Exception as e:
            logger.error(f"Error listing blobs: {e}")
            return []
    
    def delete_blob(self, blob_path: str) -> bool:
        """
        Delete a blob from the container
        
        Args:
            blob_path: Path of the blob to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.enabled or not self.container_client:
            logger.warning("Azure Blob Storage not enabled or properly initialized")
            return False
            
        try:
            # Create blob client
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Delete the blob
            blob_client.delete_blob()
            
            logger.info(f"Deleted blob {blob_path}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob {blob_path} not found in container {self.container_name}")
            return False
        except Exception as e:
            logger.error(f"Error deleting blob {blob_path}: {e}")
            return False

# Create a singleton instance
azure_blob_storage = AzureBlobStorage()
