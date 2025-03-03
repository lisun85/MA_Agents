#!/usr/bin/env python
# src/family_office_finder/main.py

import json
import os
import csv
import datetime
import re
from family_office_finder.crew import FamilyOfficeFinderCrew
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clean_json_output(output_text):
    """
    Cleans the output text to extract valid JSON.
    Handles cases where JSON is wrapped in markdown code blocks.
    """
    # Try to extract JSON from markdown code blocks if present
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output_text)
    if json_match:
        json_str = json_match.group(1)
        return json_str
    
    # If no code blocks, return the original text
    return output_text

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
        # Get current date and time for file naming
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Create date-based output directory structure
        base_output_dir = "output"
        date_dir = os.path.join(base_output_dir, current_date)
        os.makedirs(date_dir, exist_ok=True)
        
        # Get the next run number for today
        existing_runs = [d for d in os.listdir(date_dir) if os.path.isdir(os.path.join(date_dir, d))]
        run_numbers = [int(run.split("_")[1]) for run in existing_runs if run.startswith("run_")]
        next_run_number = 1 if not run_numbers else max(run_numbers) + 1
        
        # Create run directory
        run_dir = os.path.join(date_dir, f"run_{next_run_number}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Process discovery task results (first task)
        # Clean the JSON output by removing any code block wrapper
        cleaned_output = clean_json_output(result.tasks_output[0].raw)
        discovery_output = json.loads(cleaned_output)
        
        # For debugging
        print(f"Successfully parsed discovery task output")
        
        # Save as JSON with numeric identifier
        discovery_json_path = os.path.join(run_dir, f"1_family_offices_list.json")
        with open(discovery_json_path, "w") as f:
            json.dump(discovery_output, f, indent=2)
        
        # Save as CSV with numeric identifier
        discovery_csv_path = os.path.join(run_dir, f"1_family_offices_list.csv")
        
        # Extract field names from the discovery output structure
        discovery_data = []
        if isinstance(discovery_output, dict) and "family_offices" in discovery_output:
            discovery_data = discovery_output["family_offices"]
        elif isinstance(discovery_output, list):
            discovery_data = discovery_output
            
        # Create a flattened structure for CSV
        flattened_data = []
        for office in discovery_data:
            flat_office = {
                "name": office.get("name", ""),
                "url": office.get("url", ""),
                "location": office.get("location", ""),
                "estimated_aum": office.get("aum_estimate", ""),
                "investment_focus": ", ".join(office.get("investment_focus", {}).get("target_sectors", [])) if isinstance(office.get("investment_focus"), dict) else "",
                "aum_evidence": office.get("aum_evidence", ""),
                "confidence_score": office.get("confidence_score", "")
            }
            flattened_data.append(flat_office)
            
        # Write the CSV file
        if flattened_data:
            fieldnames = ["name", "url", "location", "estimated_aum", "investment_focus", "aum_evidence", "confidence_score"]
            with open(discovery_csv_path, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for office in flattened_data:
                    writer.writerow(office)
        
        # Process profile scraper task results (second task)
        profile_output = None
        if len(result.tasks_output) > 1:
            try:
                # Clean the JSON output for profile data
                cleaned_profile = clean_json_output(result.tasks_output[1].raw)
                profile_output = json.loads(cleaned_profile)
                print(f"Successfully parsed profile scraper task output")
                
                # Save as JSON with numeric identifier
                profile_json_path = os.path.join(run_dir, f"2_family_offices_profiles.json")
                with open(profile_json_path, "w") as f:
                    json.dump(profile_output, f, indent=2)
                
                # Extract profile data
                profile_data = []
                if isinstance(profile_output, dict) and "family_offices" in profile_output:
                    profile_data = profile_output["family_offices"]
                elif isinstance(profile_output, list):
                    profile_data = profile_output
                
                # Save detailed profiles as a CSV
                profile_csv_path = os.path.join(run_dir, f"2_family_offices_profiles.csv")
                
                # Create a flattened structure for CSV
                flattened_profiles = []
                for profile in profile_data:
                    # Convert complex nested structures to strings for CSV
                    leadership = ", ".join([f"{leader.get('name')} ({leader.get('role')})" 
                                         for leader in profile.get("leadership_team", [])]) if profile.get("leadership_team") else ""
                    
                    # Handle contact info
                    contact_info = profile.get("contact_info", {})
                    address = contact_info.get("address", "") if isinstance(contact_info, dict) else ""
                    phone = contact_info.get("phone", "") if isinstance(contact_info, dict) else ""
                    email = contact_info.get("email", "") if isinstance(contact_info, dict) else ""
                    
                    # Handle investment focus
                    inv_focus = profile.get("investment_focus", {})
                    target_sectors = ", ".join(inv_focus.get("target_sectors", [])) if isinstance(inv_focus, dict) else ""
                    geo_prefs = ", ".join(inv_focus.get("geographic_preferences", [])) if isinstance(inv_focus, dict) else ""
                    inv_types = ", ".join(inv_focus.get("types_of_investments", [])) if isinstance(inv_focus, dict) else ""
                    
                    flat_profile = {
                        "name": profile.get("name", ""),
                        "url": profile.get("url", ""),
                        "address": address,
                        "phone": phone,
                        "email": email,
                        "founding_year": profile.get("founding_year", ""),
                        "leadership_team": leadership,
                        "aum_estimate": profile.get("aum_estimate", ""),
                        "aum_evidence": profile.get("aum_evidence", ""),
                        "investment_philosophy": profile.get("investment_philosophy", ""),
                        "target_sectors": target_sectors,
                        "geographic_preferences": geo_prefs,
                        "investment_size": inv_focus.get("typical_investment_size", "") if isinstance(inv_focus, dict) else "",
                        "investment_types": inv_types,
                        "completeness_score": profile.get("completeness_score", "")
                    }
                    flattened_profiles.append(flat_profile)
                
                if flattened_profiles:
                    profile_fieldnames = ["name", "url", "address", "phone", "email", "founding_year", 
                                      "leadership_team", "aum_estimate", "aum_evidence", "investment_philosophy", 
                                      "target_sectors", "geographic_preferences", "investment_size", 
                                      "investment_types", "completeness_score"]
                    
                    with open(profile_csv_path, "w", newline="") as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=profile_fieldnames)
                        writer.writeheader()
                        for profile in flattened_profiles:
                            writer.writerow(profile)
            except Exception as e:
                print(f"Error processing profile results: {e}")
                import traceback
                traceback.print_exc()
        
        # Also save a combined results file
        combined_json_path = os.path.join(run_dir, f"3_combined_results.json")
        combined_data = {
            "run_info": {
                "date": current_date,
                "run_number": next_run_number,
                "timestamp": current_datetime
            },
            "discovery_results": discovery_output,
            "profile_results": profile_output if profile_output else {}
        }
        
        with open(combined_json_path, "w") as f:
            json.dump(combined_data, f, indent=2)
        
        # Save metadata about the run
        metadata_path = os.path.join(run_dir, "run_metadata.json")
        metadata = {
            "run_date": current_date,
            "run_time": current_datetime,
            "run_number": next_run_number,
            "discovery_count": len(discovery_data),
            "profile_count": len(profile_data) if profile_output else 0,
            "files_generated": [
                "1_family_offices_list.json",
                "1_family_offices_list.csv",
                "2_family_offices_profiles.json" if profile_output else "",
                "2_family_offices_profiles.csv" if profile_output else "",
                "3_combined_results.json"
            ]
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Print a summary
        print("\n==========================================")
        print("CHICAGO FAMILY OFFICE FINDER ($100M+ AUM)")
        print("==========================================")
        print(f"Discovered {len(discovery_data)} family offices in Chicago with estimated AUM of $100M+")
        print(f"Run date: {current_date}, Run #: {next_run_number}")
        print(f"All results saved to: {run_dir}")
        print("==========================================")
        print("Files generated:")
        print(f"1. {os.path.basename(discovery_json_path)}")
        print(f"2. {os.path.basename(discovery_csv_path)}")
        
        if profile_output:
            print(f"3. {os.path.basename(profile_json_path)}")
            print(f"4. {os.path.basename(profile_csv_path)}")
            
        print(f"5. {os.path.basename(combined_json_path)}")
        print("==========================================\n")
        
        # Print the first 3 results as a preview of discovered offices
        preview_count = min(3, len(discovery_data))
        if preview_count > 0:
            print("Preview of discovered high-AUM family offices:")
            for i, office in enumerate(discovery_data[:preview_count]):
                aum = office.get('aum_estimate', 'AUM not specified')
                print(f"{i+1}. {office.get('name')} - AUM: {aum} - {office.get('url', 'No URL found')}")
        
    except Exception as e:
        print(f"Error processing results: {e}")
        import traceback
        traceback.print_exc()
        print("Raw result:")
        for i, task_output in enumerate(result.tasks_output):
            print(f"Task {i+1} output:")
            print(task_output.raw[:500] + "..." if len(task_output.raw) > 500 else task_output.raw)

if __name__ == "__main__":
    run()