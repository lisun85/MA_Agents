"""
Test module for branfordcastle.com folder in S3.

This module contains test cases for verifying the branfordcastle.com folder in S3.
To run these tests, the following environment variables must be set:
- AWS_ACCESS_KEY_ID: Your AWS access key
- AWS_SECRET_ACCESS_KEY: Your AWS secret key
- AWS_S3_BUCKET_NAME: The name of the S3 bucket to test with
- AWS_REGION: (Optional) The AWS region to use (defaults to us-east-1)
"""

import unittest
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import the aws module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Get the project root directory (two levels up from current file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from the root directory .env file
load_dotenv(os.path.join(project_root, '.env'))

# Import the module to test
from backend.aws.s3 import S3Client, get_s3_client


class TestBranfordcastle(unittest.TestCase):
    """Test cases for the branfordcastle.com folder in S3 using real API calls."""
    
    def setUp(self):
        """Set up test environment."""
        # Check if required environment variables are set
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET_NAME']
        for var in required_vars:
            if not os.environ.get(var):
                self.skipTest(f"Environment variable {var} is not set")
        
        logger.info(f"Using S3 bucket: {os.environ.get('AWS_S3_BUCKET_NAME')}")
        logger.info("Setting up test environment")
        # Create S3 client for tests
        self.s3_client = get_s3_client()
        
    def tearDown(self):
        """Clean up after tests."""
        logger.info("Cleaning up test environment")
    
    def test_branfordcastle_folder_has_27_files(self):
        """
        Test case to verify that the 'branfordcastle.com' folder has exactly 27 files.
        This test uses real AWS S3 API calls.
        """
        # Get files grouped by directory
        files_by_dir = self.s3_client.list_files_by_directory()
        
        # Check if the branfordcastle.com folder exists
        self.assertIn('branfordcastle.com', files_by_dir, 
                     "The branfordcastle.com folder should exist in the bucket")
        
        # Check if the folder has exactly 27 files
        branfordcastle_files = files_by_dir['branfordcastle.com']
        logger.info(f"Found {len(branfordcastle_files)} files in branfordcastle.com folder")
        
        # Log the files for debugging
        for file_path in branfordcastle_files:
            logger.info(f"  - {file_path}")
        
        # Assert the file count
        self.assertEqual(len(branfordcastle_files), 27, 
                        "The branfordcastle.com folder should contain exactly 27 files")
        
        # Check that all files have the correct prefix
        for file_path in branfordcastle_files:
            self.assertTrue(file_path.startswith('branfordcastle.com/'),
                           f"File {file_path} should have the correct prefix")
    
    def test_portfolio_txt_exists(self):
        """
        Test case to verify that the portfolio.txt file exists in the branfordcastle.com folder.
        This test uses real AWS S3 API calls.
        """
        # Get files grouped by directory
        files_by_dir = self.s3_client.list_files_by_directory()
        
        # Check if the branfordcastle.com folder exists
        self.assertIn('branfordcastle.com', files_by_dir, 
                     "The branfordcastle.com folder should exist in the bucket")
        
        # Check if portfolio.txt exists
        branfordcastle_files = files_by_dir['branfordcastle.com']
        portfolio_file = 'branfordcastle.com/portfolio.txt'
        
        # Log all files for debugging
        logger.info(f"Found {len(branfordcastle_files)} files in branfordcastle.com folder")
        for file_path in branfordcastle_files:
            logger.info(f"  - {file_path}")
        
        # Assert the portfolio file exists
        self.assertIn(portfolio_file, branfordcastle_files, 
                     f"The portfolio.txt file should exist in the branfordcastle.com folder")
        
        # Check that we can read its content
        content = self.s3_client.get_file_content(portfolio_file)
        self.assertIsNotNone(content, "Should be able to read the portfolio.txt file")
        self.assertTrue(len(content) > 0, "The portfolio.txt file should not be empty")
        
        # Log a preview of the content
        logger.info(f"Portfolio content preview: {content[:200]}...")


# Run the tests if this file is executed directly
if __name__ == "__main__":
    unittest.main()
