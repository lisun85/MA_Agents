#!/usr/bin/env python
"""
Module for uploading scraped data to AWS S3
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class S3Uploader:
    """Class for uploading files to AWS S3"""
    
    def __init__(self):
        """Initialize the S3 uploader with credentials from environment variables"""
        # Get AWS credentials from environment variables
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-2')
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        
        # Validate required credentials
        if not self.aws_access_key or not self.aws_secret_key or not self.bucket_name:
            logger.warning("AWS credentials or bucket name not found in environment variables")
            logger.warning("Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET_NAME")
        
        # Initialize S3 client
        self.s3_client = None
        if self.aws_access_key and self.aws_secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
    
    def upload_file(self, file_path, s3_key=None):
        """
        Upload a file to S3
        
        Args:
            file_path: Local path to the file
            s3_key: S3 object key (path in the bucket). If None, uses the file name.
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        if not self.s3_client:
            logger.error("S3 client not initialized. Check your AWS credentials.")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
        
        # If no S3 key is provided, use the file name
        if s3_key is None:
            s3_key = os.path.basename(file_path)
        
        try:
            logger.info(f"Uploading {file_path} to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            logger.info(f"Successfully uploaded {file_path} to S3")
            return True
        except ClientError as e:
            logger.error(f"Error uploading {file_path} to S3: {e}")
            return False
    
    def upload_directory(self, directory_path, s3_prefix=None, recursive=True):
        """
        Upload an entire directory to S3
        
        Args:
            directory_path: Local path to the directory
            s3_prefix: Prefix to add to S3 keys (folder in the bucket)
            recursive: Whether to upload subdirectories recursively
            
        Returns:
            dict: Summary of upload results
        """
        if not self.s3_client:
            logger.error("S3 client not initialized. Check your AWS credentials.")
            return {"success": False, "error": "S3 client not initialized"}
        
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return {"success": False, "error": f"Directory not found: {directory_path}"}
        
        # Initialize counters
        total_files = 0
        successful_uploads = 0
        failed_uploads = 0
        
        # Walk through the directory
        for root, dirs, files in os.walk(directory_path):
            # Skip if not recursive and we're in a subdirectory
            if not recursive and root != directory_path:
                continue
            
            for file in files:
                total_files += 1
                file_path = os.path.join(root, file)
                
                # Calculate the S3 key (path in the bucket)
                relative_path = os.path.relpath(file_path, directory_path)
                if s3_prefix:
                    s3_key = f"{s3_prefix}/{relative_path}"
                else:
                    s3_key = relative_path
                
                # Upload the file
                if self.upload_file(file_path, s3_key):
                    successful_uploads += 1
                else:
                    failed_uploads += 1
        
        # Return summary
        return {
            "success": failed_uploads == 0,
            "total_files": total_files,
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads
        }

def upload_output_to_s3(output_dir=None, bucket_name=None):
    """
    Upload the output directory to S3
    
    Args:
        output_dir: Path to the output directory. If None, uses the default.
        bucket_name: S3 bucket name. If None, uses the one from environment variables.
        
    Returns:
        dict: Summary of upload results
    """
    # Initialize the uploader
    uploader = S3Uploader()
    
    # Override bucket name if provided
    if bucket_name:
        uploader.bucket_name = bucket_name
    
    # Determine the output directory
    if not output_dir:
        # Use the default output directory from the playwright scraper
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
    
    # Check if the directory exists
    if not os.path.exists(output_dir):
        logger.error(f"Output directory not found: {output_dir}")
        return {"success": False, "error": f"Output directory not found: {output_dir}"}
    
    # Upload the directory
    logger.info(f"Uploading output directory {output_dir} to S3 bucket {uploader.bucket_name}")
    result = uploader.upload_directory(output_dir, s3_prefix="scraped_data")
    
    if result["success"]:
        logger.info(f"Successfully uploaded {result['successful_uploads']} files to S3")
    else:
        logger.warning(f"Uploaded {result['successful_uploads']} files with {result['failed_uploads']} failures")
    
    return result

def test_aws_connection():
    """Test AWS S3 connection and credentials"""
    # Create a custom uploader with hardcoded credentials for testing
    uploader = S3Uploader()
    
    # # IMPORTANT: Replace these with your actual credentials for testing
    # # Remove or comment out these lines before committing to version control
    # uploader.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    # uploader.aws_secret_key = "AWS_SECRET_ACCESS_KEY"
    # uploader.aws_region = "us-east-2"  # Change if needed
    # uploader.bucket_name = "AWS_S3_BUCKET_NAME"
    
    # Reinitialize the S3 client with the new credentials
    uploader.s3_client = boto3.client(
        's3',
        aws_access_key_id=uploader.aws_access_key,
        aws_secret_access_key=uploader.aws_secret_key,
        region_name=uploader.aws_region
    )
    
    if not uploader.s3_client:
        logger.error("Failed to initialize S3 client. Check your AWS credentials.")
        return False
    
    try:
        # Try to list buckets (this requires valid credentials)
        response = uploader.s3_client.list_buckets()
        
        # Print bucket information
        logger.info("AWS connection successful!")
        logger.info(f"Your AWS account has {len(response['Buckets'])} buckets:")
        
        for bucket in response['Buckets']:
            logger.info(f"- {bucket['Name']} (created: {bucket['CreationDate']})")
        
        # Check if the configured bucket exists
        bucket_exists = any(bucket['Name'] == uploader.bucket_name for bucket in response['Buckets'])
        
        if bucket_exists:
            logger.info(f"✅ Configured bucket '{uploader.bucket_name}' exists and is accessible")
            
            # Try to list objects in the bucket
            try:
                objects = uploader.s3_client.list_objects_v2(Bucket=uploader.bucket_name, MaxKeys=5)
                
                if 'Contents' in objects and objects['Contents']:
                    logger.info(f"Sample objects in bucket:")
                    for obj in objects['Contents'][:5]:
                        logger.info(f"- {obj['Key']} ({obj['Size']} bytes)")
                else:
                    logger.info(f"Bucket is empty or you don't have permission to list objects")
                    
            except Exception as e:
                logger.warning(f"Could not list objects in bucket: {e}")
        else:
            logger.warning(f"⚠️ Configured bucket '{uploader.bucket_name}' does not exist or is not accessible")
            
        return True
        
    except Exception as e:
        logger.error(f"AWS connection test failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload scraped data to AWS S3')
    parser.add_argument('--dir', '-d', help='Path to the output directory to upload')
    parser.add_argument('--bucket', '-b', help='S3 bucket name (overrides environment variable)')
    parser.add_argument('--test', '-t', action='store_true', help='Test AWS connection')
    
    args = parser.parse_args()
    
    if args.test:
        test_aws_connection()
    else:
        upload_output_to_s3(args.dir, args.bucket)
