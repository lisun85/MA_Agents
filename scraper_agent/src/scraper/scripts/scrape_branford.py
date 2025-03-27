#!/usr/bin/env python
"""
Script to scrape Branford Castle Partners website using the profile agent
"""

import os
import sys
import json
import datetime
import logging
from scraper.crew import FamilyOfficeFinderCrew

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the scraper for Branford Castle Partners"""
    # URL and name for Branford Castle Partners
    url_to_scrape = "https://branfordcastle.com/"
    office_name = "Branford Castle Partners"
    
    logger.info(f"Scraping {office_name} at {url_to_scrape}")
    
    # Create the crew instance
    crew_instance = FamilyOfficeFinderCrew()
    
    # Create a context with the provided URL
    context = {
        "discovered_offices": [
            {"name": office_name, "website": url_to_scrape}
        ]
    }
    
    # Execute profile task directly
    logger.info(f"Executing profile task...")
    profile_task = crew_instance.profile_scraper_task()
    profile_agent = crew_instance.family_office_profile_agent()
    profile_result = profile_agent.execute_task(profile_task, context=context)
    
    # Save the profile output to files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("output", f"branford_castle_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as text file
    with open(os.path.join(output_dir, "branford_castle_profile.txt"), "w") as f:
        f.write(profile_result)
    
    # Try to parse as JSON and save if possible
    try:
        # Try to extract JSON from the result if it's embedded in text
        json_data = None
        import re
        json_match = re.search(r'```json\n(.*?)\n```', profile_result, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
            json_data = json.loads(json_str)
        else:
            # Try to parse the entire result as JSON
            try:
                json_data = json.loads(profile_result)
            except:
                # If that fails, create a structured JSON from the text
                json_data = {
                    "name": office_name,
                    "url": url_to_scrape,
                    "profile_data": profile_result,
                    "timestamp": timestamp
                }
        
        # Save as JSON
        with open(os.path.join(output_dir, "branford_castle_profile.json"), "w") as f:
            json.dump(json_data, f, indent=2)
            
        logger.info(f"Profile results saved to {output_dir}/branford_castle_profile.txt and .json")
        
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        logger.info(f"Profile results saved to {output_dir}/branford_castle_profile.txt only")

if __name__ == "__main__":
    main() 