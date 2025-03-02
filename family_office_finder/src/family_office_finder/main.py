#!/usr/bin/env python
# src/family_office_finder/main.py

import json
import os
from family_office_finder.crew import FamilyOfficeFinderCrew
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run():
    """
    Run the Family Office Finder crew to discover family offices in Chicago.
    """
    # Initialize the crew
    crew = FamilyOfficeFinderCrew().crew()
    
    # Run the crew
    result = crew.kickoff()
    
    # Process and store the results
    try:
        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Process discovery task results (first task)
        discovery_output = json.loads(result.tasks_output[0].raw)
        with open(f"{output_dir}/chicago_family_offices_list.json", "w") as f:
            json.dump(discovery_output, f, indent=2)
        
        # Save a CSV of just the names and URLs
        import csv
        with open(f"{output_dir}/chicago_family_offices_list.csv", "w", newline="") as csvfile:
            fieldnames = ["name", "url", "location", "investment_focus", "confidence_score"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for office in discovery_output:
                writer.writerow({
                    "name": office.get("name", ""),
                    "url": office.get("url", ""),
                    "location": office.get("location", ""),
                    "investment_focus": office.get("investment_focus", ""),
                    "aum_evidence": office.get("aum_evidence", ""),
                    "confidence_score": office.get("confidence_score", "")
                })
        
        # Process profile scraper task results (second task)
        if len(result.tasks_output) > 1:
            profile_output = json.loads(result.tasks_output[1].raw)
            with open(f"{output_dir}/chicago_family_offices_profiles.json", "w") as f:
                json.dump(profile_output, f, indent=2)
                
            # Save detailed profiles as a CSV 
            profile_fieldnames = ["name", "url", "address", "phone", "email", "founding_year", 
                                  "leadership_team", "aum_estimate", "aum_evidence", "investment_philosophy", "target_sectors", 
                                  "geographic_preferences", "investment_size", "investment_types", 
                                  "portfolio_companies", "completeness_score"]
            
            with open(f"{output_dir}/chicago_family_offices_profiles.csv", "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=profile_fieldnames, extrasaction='ignore')
                writer.writeheader()
                for profile in profile_output:
                    writer.writerow(profile)
        
        # Print a summary
        print("\n==========================================")
        print("CHICAGO FAMILY OFFICE FINDER ($100M+ AUM)")
        print(f"Discovered {len(discovery_output)} family offices in Chicago with estimated AUM of $100M+")
        print(f"Basic list saved to {output_dir}/chicago_family_offices_list.json")
        
        
        if len(result.tasks_output) > 1:
            print(f"Created {len(profile_output)} detailed profiles")
            print(f"Detailed profiles saved to {output_dir}/chicago_family_offices_profiles.json")
        
        print("==========================================\n")
        
        # Print the first 3 results as a preview of discovered offices
        print("Preview of discovered high-AUM family offices:")
        for i, office in enumerate(discovery_output[:3]):
            aum = office.get('estimated_aum', 'AUM not specified')
            print(f"{i+1}. {office.get('name')} - AUM: {aum} - {office.get('url', 'No URL found')}")
        
    except Exception as e:
        print(f"Error processing results: {e}")
        print("Raw result:", result.raw)

if __name__ == "__main__":
    run()