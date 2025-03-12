#!/usr/bin/env python
"""
Main entry point for the FamilyOfficeFinder Crew
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from family_office_finder.crew import FamilyOfficeFinderCrew

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run():
    """Run the FamilyOfficeFinder crew to scrape websites"""
    logger.info("Starting FamilyOfficeFinder web scraper...")
    
    # Default URLs file path
    urls_file = "urls_to_scrape.txt"
    
    # Check if the URLs file exists
    if not os.path.exists(urls_file):
        logger.error(f"URLs file not found: {urls_file}")
        logger.info("Creating a sample URLs file...")
        
        # Create a sample URLs file
        with open(urls_file, 'w') as f:
            f.write("# List of URLs to scrape (one per line)\n")
            f.write("# Lines starting with # are ignored\n\n")
            f.write("https://branfordcastle.com/\n")
            f.write("# Add more URLs as needed\n")
        
        logger.info(f"Sample URLs file created: {urls_file}")
        logger.info("Please edit this file to add your URLs, then run again.")
        return 1
    
    # Create and run the crew
    crew = FamilyOfficeFinderCrew()
    result = crew.run(urls_file)
    
    # Print the result
    if hasattr(result, 'success') and not result.success:
        logger.error(f"Crew execution failed: {result.output}")
        return 1
    
    logger.info("Web scraping completed successfully")
    logger.info(f"Result: {result}")
    
    # Print a helpful message about where to find the output
    output_dir = os.path.expanduser("~/Documents/Github/MA_Agents/family_office_finder/output")
    logger.info(f"All scraped content is saved to: {output_dir}")
    logger.info("For each website, a timestamped directory was created containing:")
    logger.info("- JSON files with full page data")
    logger.info("- TXT files with readable text content")
    logger.info("- A crawl_summary.json file with metadata about the crawl")
    
    return 0

def train():
    """Train the FamilyOfficeFinder models (placeholder)"""
    logger.info("Training not implemented yet")
    return 0

def replay():
    """Replay a previous run (placeholder)"""
    logger.info("Replay not implemented yet")
    return 0

def test():
    """Run tests (placeholder)"""
    logger.info("Tests not implemented yet")
    return 0

if __name__ == "__main__":
    sys.exit(run())
