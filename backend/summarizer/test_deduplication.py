"""
Test script to run parallel summarizer on specific company files in S3.

This script runs the summarizer on selected company files to test deduplication.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import boto3
from dotenv import load_dotenv
import json

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(str(project_root / ".env"))

# Import the Summarizer class - adjust the import path if needed
from backend.summarizer.summarizer import Summarizer
from backend.aws.s3 import get_s3_client
from backend.summarizer.parallel_extraction import ParallelExtractionManager, CompilationAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("deduplication_test.log")
    ]
)
logger = logging.getLogger("deduplication_test")

# Target company directories to test
TARGET_COMPANIES = [
    "gennx360.com",
    "granitecreek.com",
    "hadleycapital.com",
    "heartwoodpartners.com",
    "middleground.com",
    "rljequitypartners.com"
]

# Define output directory (modified to use a specific directory)
OUTPUT_DIR = Path(__file__).parent / "output" / "DeduplicationTest"

async def run_test():
    """Run the test on target company files."""
    logger.info(f"Starting deduplication test on companies: {', '.join(TARGET_COMPANIES)}")
    
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output will be saved to: {OUTPUT_DIR}")
    
    # Initialize the S3 client
    s3_client = get_s3_client()
    
    # Loop through each target company
    for company_dir in TARGET_COMPANIES:
        try:
            logger.info(f"Processing company directory: {company_dir}")
            
            # Create a summarizer instance
            summarizer = Summarizer()
            summarizer.current_firm_name = company_dir.split('.')[0]  # Remove domain extension
            
            # Create parallel extraction manager
            parallel_manager = ParallelExtractionManager(summarizer)
            
            # Create compilation agent for deduplication
            compilation_agent = CompilationAgent(summarizer)
            
            # Get a list of files for this company
            files = list_files_for_company(s3_client, company_dir)
            
            if not files:
                logger.warning(f"No files found for company {company_dir}")
                continue
                
            logger.info(f"Found {len(files)} files for {company_dir}")
            
            # Download the files and read their contents
            file_contents = download_company_files(s3_client, files)
            
            if not file_contents:
                logger.warning(f"Failed to download files for {company_dir}")
                continue
            
            # Run parallel extraction directly
            raw_result = await parallel_manager.run_parallel_extraction(file_contents, company_dir)
            
            # Apply additional deduplication using the compilation agent
            logger.info("Applying additional deduplication to results")
            for section_name, section_data in raw_result["summary"].items():
                if section_name == "media_and_news":
                    # Deduplicate media content (this is a list of extract dictionaries)
                    raw_result["summary"][section_name] = compilation_agent._deduplicate_extracts_list(section_data)
                    logger.info(f"Deduplicated media_and_news section: {len(section_data)} -> {len(raw_result['summary'][section_name])}")
                elif section_name == "investment_strategy" and "extracts" in section_data:
                    # Deduplicate investment strategy extracts
                    raw_result["summary"][section_name]["extracts"] = compilation_agent._deduplicate_extracts_list(section_data["extracts"])
                    logger.info(f"Deduplicated investment_strategy extracts: {len(section_data['extracts'])} -> {len(raw_result['summary'][section_name]['extracts'])}")
                elif section_name in ["industry_focus", "geographic_focus"] and "extracts" in section_data:
                    # Deduplicate focus extracts
                    raw_result["summary"][section_name]["extracts"] = compilation_agent._deduplicate_extracts_list(section_data["extracts"])
                    # Deduplicate focus summary text
                    raw_result["summary"][section_name]["summary"] = compilation_agent._deduplicate_text_content(section_data["summary"])
                elif section_name == "team_and_contacts":
                    # Deduplicate team and contacts list
                    raw_result["summary"][section_name] = compilation_agent._deduplicate_extracts_list(section_data)
                    logger.info(f"Deduplicated team_and_contacts section: {len(section_data)} -> {len(raw_result['summary'][section_name])}")
                elif section_name == "portfolio_companies":
                    # Deduplicate portfolio companies
                    raw_result["summary"][section_name] = compilation_agent._deduplicate_structured_content(section_data)
                    logger.info(f"Deduplicated portfolio_companies section: {len(section_data)} -> {len(raw_result['summary'][section_name])}")
            
            # Output results
            if raw_result:
                # Save JSON output in the specified output directory
                output_path = OUTPUT_DIR / f"test_output_{company_dir}.json"
                with open(output_path, 'w') as f:
                    json.dump(raw_result, f, indent=2)
                logger.info(f"Summary for {company_dir} saved to {output_path}")
                
                # Generate text summary using the summarizer's generate_summary_report function
                text_output_path = OUTPUT_DIR / f"test_output_{company_dir}.txt"
                text_report = summarizer.generate_summary_report(raw_result)
                with open(text_output_path, 'w') as f:
                    f.write(text_report)
                logger.info(f"Text summary for {company_dir} saved to {text_output_path}")
                
                # Log deduplication stats
                log_deduplication_stats(company_dir, raw_result["summary"])
            else:
                logger.error(f"Failed to generate summary for {company_dir}")
                
        except Exception as e:
            logger.exception(f"Error processing {company_dir}: {str(e)}")
    
    logger.info("Test completed")

def list_files_for_company(s3_client, company_dir):
    """List all files for a specific company in S3."""
    try:
        # Get the bucket name from environment
        bucket_name = os.environ.get("AWS_S3_BUCKET_NAME")
        if not bucket_name:
            logger.error("AWS_S3_BUCKET_NAME environment variable not set")
            return []
        
        # Use the list_files_by_directory method instead of list_objects_v2
        files_by_directory = s3_client.list_files_by_directory()
        
        if not files_by_directory or company_dir not in files_by_directory:
            logger.warning(f"No files found for {company_dir}")
            return []
            
        # Return the file keys for this company directory
        files = files_by_directory.get(company_dir, [])
        logger.info(f"Found {len(files)} files for {company_dir}")
        return files
        
    except Exception as e:
        logger.exception(f"Error listing files for {company_dir}: {str(e)}")
        return []

def download_company_files(s3_client, file_keys):
    """Download and read contents of S3 files."""
    try:
        file_contents = {}
        
        for key in file_keys:
            try:
                logger.info(f"Downloading file: {key}")
                # Use get_file_content method instead of get_object
                content = s3_client.get_file_content(key)
                if content:
                    file_contents[key] = content
                else:
                    logger.warning(f"No content retrieved for file {key}")
            except Exception as e:
                logger.error(f"Error downloading file {key}: {str(e)}")
        
        return file_contents
        
    except Exception as e:
        logger.exception(f"Error downloading files: {str(e)}")
        return {}

def log_deduplication_stats(company_dir, summary_data):
    """Log statistics about the deduplication process."""
    try:
        # Log section-specific stats
        for section, data in summary_data.items():
            if section == "investment_strategy":
                extracts = data.get("extracts", [])
                source_files = data.get("source_files", [])
                logger.info(f"{company_dir} - Investment strategy: {len(extracts)} extracts from {len(source_files)} files")
            
            elif section == "industry_focus":
                extracts = data.get("extracts", [])
                logger.info(f"{company_dir} - Industry focus: {len(extracts)} extracts")
            
            elif section == "geographic_focus":
                extracts = data.get("extracts", [])
                logger.info(f"{company_dir} - Geographic focus: {len(extracts)} extracts")
            
            elif section == "team_and_contacts":
                logger.info(f"{company_dir} - Team members: {len(data)}")
            
            elif section == "portfolio_companies":
                logger.info(f"{company_dir} - Portfolio companies: {len(data)}")
            
            elif section == "media_and_news":
                logger.info(f"{company_dir} - Media items: {len(data)}")
        
    except Exception as e:
        logger.error(f"Error logging deduplication stats: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_test()) 