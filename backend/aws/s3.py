import os
import boto3
from collections import defaultdict
from dotenv import load_dotenv
from typing import Dict, List, Optional
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Get the project root directory (two levels up from current file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from the root directory .env file
load_dotenv(os.path.join(project_root, '.env'))

class S3Client:
    def __init__(self):
        """Initialize the S3 client with credentials from environment variables."""
        try:
            self.bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
            if not self.bucket_name:
                raise ValueError("AWS_S3_BUCKET_NAME environment variable is not set")
            
            # Initialize the S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=os.environ.get("AWS_REGION", "us-east-1")
            )
            logger.info(f"S3 client initialized with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error initializing S3 client: {str(e)}")
            raise

    def list_files_by_directory(self) -> Dict[str, List[str]]:
        """List all files in the S3 bucket, grouped by directory.
        Includes files in subdirectories, maintaining their full paths.
        
        Returns:
            Dict[str, List[str]]: A dictionary with directory names as keys and 
                                 lists of file paths as values.
        """
        try:
            # Initialize a defaultdict to store files by directory
            files_by_directory = defaultdict(list)
            
            # List all objects in the bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)
            
            # Process each object
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        
                        # Skip if the object is a directory marker (ends with '/')
                        if key.endswith('/'):
                            continue
                        
                        # Determine the directory for this file
                        parts = key.split('/')
                        if len(parts) > 1:
                            # File is in a subdirectory
                            directory = parts[0]
                            files_by_directory[directory].append(key)
                        else:
                            # File is in the root directory
                            files_by_directory['root'].append(key)
            
            logger.info(f"Found files in {len(files_by_directory)} directories")
            return dict(files_by_directory)
        
        except Exception as e:
            logger.error(f"Error listing files by directory: {str(e)}")
            return {}

    def get_files_content_by_directory(self, directory_name: str) -> List[str]:
        """Retrieve the content of all files in a specific directory as a list of strings.
        Includes files in subdirectories.
        
        Args:
            directory_name (str): The name of the directory to retrieve files from
            
        Returns:
            List[str]: A list of file contents as strings
        """
        try:
            # Get files in the directory
            files_by_dir = self.list_files_by_directory()
            if directory_name not in files_by_dir:
                logger.warning(f"Directory '{directory_name}' not found in bucket")
                return []
            
            file_paths = files_by_dir[directory_name]
            file_contents = []
            
            # Retrieve content for each file
            for file_path in file_paths:
                try:
                    response = self.s3_client.get_object(
                        Bucket=self.bucket_name,
                        Key=file_path
                    )
                    
                    # Read the file content
                    content = response['Body'].read().decode('utf-8')
                    file_contents.append(content)
                    
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    # Add an empty string or error message for this file
                    file_contents.append(f"Error reading file: {file_path}")
            
            logger.info(f"Retrieved content for {len(file_contents)} files from directory '{directory_name}'")
            return file_contents
            
        except Exception as e:
            logger.error(f"Error retrieving file contents for directory '{directory_name}': {str(e)}")
            return []

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Retrieve the content of a specific file from S3.
        
        Args:
            file_path (str): The path to the file in the S3 bucket
            
        Returns:
            Optional[str]: The file content as a string, or None if an error occurs
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            
            # Read the file content
            content = response['Body'].read().decode('utf-8')
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving content for file '{file_path}': {str(e)}")
            return None

# Create a singleton instance
s3_client = None

def get_s3_client() -> S3Client:
    """Get or create the S3 client singleton instance.
    
    Returns:
        S3Client: The S3 client instance
    """
    global s3_client
    if s3_client is None:
        s3_client = S3Client()
    return s3_client