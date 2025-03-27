"""
Test module for S3 utilities using mock data.

This module contains test cases for the S3 client functionality using mock data.
"""

import unittest
import os
import sys
import logging
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import the aws module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the module to test
from backend.aws.s3 import S3Client, get_s3_client


class TestS3Client(unittest.TestCase):
    """Test cases for the S3Client class using mock data."""
    
    def setUp(self):
        """Set up test environment."""
        logger.info("Setting up test environment with mock data")
        self.mock_s3_client = MagicMock()
        
    def tearDown(self):
        """Clean up after tests."""
        logger.info("Cleaning up test environment")
    
    @patch('boto3.client')
    def test_s3_client_initialization(self, mock_boto_client):
        """Test that S3Client is properly initialized with environment variables."""
        # Setup mock
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock environment variables
        test_env_vars = {
            'AWS_ACCESS_KEY_ID': 'test_access_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret_key',
            'AWS_S3_BUCKET_NAME': 'test-bucket',
            'AWS_REGION': 'us-west-2'
        }
        
        # Test with mocked environment variables
        with patch.dict(os.environ, test_env_vars):
            # Initialize the client
            s3_client = S3Client()
            
            # Verify boto3.client was called with the right parameters
            mock_boto_client.assert_called_once_with(
                's3',
                aws_access_key_id='test_access_key',
                aws_secret_access_key='test_secret_key',
                region_name='us-west-2'
            )
            
            # Verify bucket name was set correctly
            self.assertEqual('test-bucket', s3_client.bucket_name)
            
            logger.info("Successfully tested S3Client initialization with mocked environment variables")
    
    @patch('boto3.client')
    def test_missing_bucket_name(self, mock_boto_client):
        """Test that S3Client raises an error when AWS_S3_BUCKET_NAME is not set."""
        # Setup mock
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock environment variables without bucket name
        test_env_vars = {
            'AWS_ACCESS_KEY_ID': 'test_access_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret_key',
            # AWS_S3_BUCKET_NAME is intentionally omitted
            'AWS_REGION': 'us-west-2'
        }
        
        # Test with mocked environment variables
        with patch.dict(os.environ, test_env_vars, clear=True):
            # Initialize the client should raise an error
            with self.assertRaises(ValueError) as context:
                s3_client = S3Client()
            
            # Verify the error message
            self.assertIn("AWS_S3_BUCKET_NAME environment variable is not set", str(context.exception))
            
            logger.info("Successfully tested S3Client raises error when bucket name is missing")


# Run the tests if this file is executed directly
if __name__ == "__main__":
    unittest.main()
