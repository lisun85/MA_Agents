"""
Test script to extract and save just the portfolio.txt file from S3.

This script connects to S3, pulls only the portfolio.txt file from
the branfordcastle.com directory, and saves it to the local output folder.
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Import the S3 client
from backend.aws.s3 import get_s3_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def extract_portfolio_file():
    """
    Extract portfolio.txt from S3 and save it to the local output directory.
    """
    # Initialize S3 client
    logger.info("Initializing S3 client")
    s3_client = get_s3_client()
    
    # Directory name
    directory_name = "branfordcastle.com"
    
    # List files in the directory
    logger.info(f"Listing files in directory: {directory_name}")
    files_by_dir = s3_client.list_files_by_directory()
    
    if directory_name not in files_by_dir:
        logger.error(f"Directory '{directory_name}' not found in S3 bucket")
        return False
    
    file_paths = files_by_dir[directory_name]
    logger.info(f"Found {len(file_paths)} files in directory '{directory_name}'")
    
    # Find the portfolio.txt file
    portfolio_file = None
    for file_path in file_paths:
        if file_path.lower().endswith('portfolio.txt'):
            portfolio_file = file_path
            break
    
    if not portfolio_file:
        logger.error("No portfolio.txt file found in the directory")
        return False
    
    logger.info(f"Found portfolio file: {portfolio_file}")
    
    # Get the content of the portfolio file
    try:
        content = s3_client.get_file_content(portfolio_file)
        if not content:
            logger.error(f"Failed to get content for file: {portfolio_file}")
            return False
        
        logger.info(f"Successfully retrieved content for {portfolio_file}")
        
        # Create output directory if it doesn't exist
        output_dir = current_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Save to file
        output_path = output_dir / "portfolio.txt"
        with open(output_path, "w") as f:
            f.write(content)
        
        logger.info(f"Saved portfolio file to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error retrieving file content: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    logger.info("Starting portfolio file extraction")
    
    success = extract_portfolio_file()
    
    if success:
        logger.info("Portfolio file extraction completed successfully")
        return 0
    else:
        logger.error("Portfolio file extraction failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 