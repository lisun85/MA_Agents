#!/usr/bin/env python
# src/family_office_finder/main.py

import json
import os
import csv
import datetime
import re
import logging
from family_office_finder.crew import FamilyOfficeFinderCrew
from dotenv import load_dotenv
import warnings
import time
import random

# Add this at the top of your main.py file
#warnings.filterwarnings("ignore", category=DeprecationWarning)
#warnings.filterwarnings("ignore", category=UserWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class JsonProcessor:
    """Class for processing and cleaning JSON outputs from agents"""

    @staticmethod
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
        
        # Look for JSON arrays
        if output_text.strip().startswith('[') and ']' in output_text:
            # Find balanced brackets
            open_brackets = 0
            for i, char in enumerate(output_text):
                if char == '[':
                    open_brackets += 1
                elif char == ']':
                    open_brackets -= 1
                    if open_brackets == 0:
                        # Found the end of the JSON array
                        return output_text[:i+1]
        
        # Look for JSON objects
        if output_text.strip().startswith('{') and '}' in output_text:
            # Find balanced braces
            open_braces = 0
            for i, char in enumerate(output_text):
                if char == '{':
                    open_braces += 1
                elif char == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        # Found the end of the JSON object
                        return output_text[:i+1]
        
        # Return the original as a fallback
        return output_text

    @staticmethod
    def parse_json(json_str):
        """
        Attempts to parse JSON with several fallback strategies.
        Returns parsed JSON or None if all attempts fail.
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parsing failed: {e}")
            try:
                # Fix common JSON issues
                fixed_json = json_str.replace("'", "\"")
                # Fix trailing commas
                fixed_json = re.sub(r',\s*}', '}', fixed_json)
                fixed_json = re.sub(r',\s*\]', ']', fixed_json)
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                # Try to extract JSON pattern as last resort
                json_pattern = r'(\[[\s\S]*\]|\{[\s\S]*\})'
                match = re.search(json_pattern, json_str)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        logger.error(f"All JSON parsing attempts failed")
                        return None
                return None

class FileManager:
    """Class for managing file operations and directory structure"""
    
    def __init__(self, base_output_dir="output"):
        self.base_output_dir = base_output_dir
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.date_dir = os.path.join(base_output_dir, self.current_date)
        self.run_dir, self.run_number = self._create_run_directory()
    
    def _create_run_directory(self):
        """Create a date-based output directory with incremental run numbers"""
        os.makedirs(self.date_dir, exist_ok=True)
        
        # Get the next run number for today
        existing_runs = [d for d in os.listdir(self.date_dir) if os.path.isdir(os.path.join(self.date_dir, d))]
        run_numbers = [int(run.split("_")[1]) for run in existing_runs if run.startswith("run_")]
        next_run_number = 1 if not run_numbers else max(run_numbers) + 1
        
        # Create run directory
        run_dir = os.path.join(self.date_dir, f"run_{next_run_number}")
        os.makedirs(run_dir, exist_ok=True)
        
        return run_dir, next_run_number
    
    def save_json(self, data, filename):
        """Save data to JSON file in the run directory"""
        if data is None:
            logger.warning(f"No data to save for {filename}")
            return None
            
        file_path = os.path.join(self.run_dir, filename)
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved {filename}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving JSON file {filename}: {e}")
            return None
    
    def save_csv(self, data, filename, fieldnames):
        """Save data to CSV file in the run directory"""
        if not data:
            logger.warning(f"No data to save for {filename}")
            return None
            
        file_path = os.path.join(self.run_dir, filename)
        try:
            with open(file_path, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                if isinstance(data, list):
                    for row in data:
                        writer.writerow(row)
                else:
                    writer.writerow(data)
            logger.info(f"Successfully saved {filename}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving CSV file {filename}: {e}")
            return None

class DataProcessor:
    """Class for processing and formatting agent output data"""
    
    @staticmethod
    def standardize_discovery_data(data):
        """Standardize discovery data structure and extract family offices list"""
        discovery_data = []
        
        if isinstance(data, dict):
            if "family_offices" in data:
                discovery_data = data["family_offices"]
            elif "family_office_profiles" in data:
                discovery_data = data["family_office_profiles"]
        elif isinstance(data, list):
            discovery_data = data
            
        # Log the discovery data for debugging
        logger.info(f"Standardized discovery data contains {len(discovery_data)} family offices")
        return discovery_data
    
    @staticmethod
    def format_discovery_for_csv(offices):
        """Format discovery data for CSV output"""
        flattened_data = []
        
        for office in offices:
            investment_focus = ""
            if "investment_focus" in office:
                if isinstance(office["investment_focus"], dict) and "target_sectors" in office["investment_focus"]:
                    investment_focus = ", ".join(office["investment_focus"]["target_sectors"])
                elif isinstance(office["investment_focus"], str):
                    investment_focus = office["investment_focus"]
            
            flat_office = {
                "name": office.get("name", ""),
                "url": office.get("url", ""),
                "location": office.get("location", ""),
                "estimated_aum": office.get("aum_estimate", office.get("estimated_aum", "")),
                "investment_focus": investment_focus,
                "aum_evidence": office.get("aum_evidence", ""),
                "confidence_score": office.get("confidence_score", "")
            }
            flattened_data.append(flat_office)
        
        return flattened_data
    
    @staticmethod
    def format_profiles_for_csv(profiles):
        """Format profile data for CSV output"""
        flattened_data = []
        
        for profile in profiles:
            flat_profile = {}
            
            # Basic fields
            flat_profile["name"] = profile.get("name", "")
            flat_profile["url"] = profile.get("url", "") or profile.get("website", "")
            flat_profile["location"] = profile.get("location", "")
            
            # Contact info
            contact_info = profile.get("contact_info", {})
            if isinstance(contact_info, dict):
                flat_profile["address"] = contact_info.get("address", "")
                flat_profile["phone"] = contact_info.get("phone", "")
                flat_profile["email"] = contact_info.get("email", "")
            else:
                flat_profile["address"] = ""
                flat_profile["phone"] = ""
                flat_profile["email"] = ""
            
            # Team members
            team_members = profile.get("team_members", [])
            if isinstance(team_members, list):
                flat_profile["team_members"] = ", ".join([f"{m.get('name', '')} ({m.get('title', '')})" for m in team_members if isinstance(m, dict)])
            else:
                flat_profile["team_members"] = ""
            
            # AUM
            flat_profile["aum"] = profile.get("aum", "") or profile.get("aum_estimate", "")
            flat_profile["aum_evidence"] = profile.get("aum_evidence", "")
            
            # Investment details
            investment_details = profile.get("investment_details", {})
            if isinstance(investment_details, dict):
                flat_profile["investment_focus"] = investment_details.get("target_sectors", "")
                flat_profile["investment_philosophy"] = investment_details.get("philosophy", "")
                flat_profile["geographic_preferences"] = investment_details.get("geographic_preferences", "")
                flat_profile["typical_investment_size"] = investment_details.get("typical_investment_size", "")
            else:
                flat_profile["investment_focus"] = profile.get("investment_focus", "")
                flat_profile["investment_philosophy"] = ""
                flat_profile["geographic_preferences"] = ""
                flat_profile["typical_investment_size"] = ""
            
            # Additional fields that might be present
            flat_profile["founding_year"] = profile.get("founding_year", "")
            flat_profile["investment_types"] = profile.get("investment_types", "")
            flat_profile["completeness_score"] = profile.get("completeness_score", "")
            
            flattened_data.append(flat_profile)
        
        return flattened_data
    
    @staticmethod
    def format_news_for_csv(news_data):
        """Format news data for CSV output"""
        flattened_news = []
        
        for office_news in news_data:
            office_name = office_news.get("name", "")
            
            # Handle recent activities
            recent_activities = office_news.get("recent_activities", [])
            if recent_activities:
                for activity in recent_activities:
                    flat_news = {
                        "name": office_name,
                        "activity_date": activity.get("date", ""),
                        "activity_headline": activity.get("headline", ""),
                        "activity_description": activity.get("description", ""),
                        "activity_source": activity.get("source", ""),
                        "activity_url": activity.get("url", ""),
                        "activity_type": activity.get("activity_type", ""),
                        "full_text": activity.get("full_text", ""),
                        "strategy_insights": office_news.get("strategy_insights", ""),
                        "leadership_changes": office_news.get("leadership_changes", ""),
                        "news_presence_score": office_news.get("news_presence_score", "")
                    }
                    flattened_news.append(flat_news)
            else:
                # Add a single entry even if no activities are found
                flat_news = {
                    "name": office_name,
                    "activity_date": "",
                    "activity_headline": "",
                    "activity_description": "",
                    "activity_source": "",
                    "activity_url": "",
                    "activity_type": "",
                    "full_text": "",
                    "strategy_insights": office_news.get("strategy_insights", ""),
                    "leadership_changes": office_news.get("leadership_changes", ""),
                    "news_presence_score": office_news.get("news_presence_score", "")
                }
                flattened_news.append(flat_news)
        
        return flattened_news

class ResultsProcessor:
    """Class for processing and saving results from the crew execution"""
    
    def __init__(self, file_manager, json_processor, data_processor):
        self.file_manager = file_manager
        self.json_processor = json_processor
        self.data_processor = data_processor
        self.results = {
            "discovery": None,
            "profiles": None,
            "news": None
        }
        self.counts = {
            "discovery": 0,
            "profiles": 0,
            "news": 0
        }
        self.generated_files = []
    
    def process_discovery_output(self, task_output):
        """Process discovery task output"""
        try:
            # Clean the JSON output by removing any code block wrapper
            cleaned_output = self.json_processor.clean_json_output(task_output.raw)
            
            # Try to parse the JSON
            discovery_output = self.json_processor.parse_json(cleaned_output)
            
            if not discovery_output:
                logger.warning("Failed to parse discovery output, trying alternative parsing")
                # Try to extract JSON from the text using regex
                json_pattern = r'({[\s\S]*})'
                json_match = re.search(json_pattern, task_output.raw)
                if json_match:
                    try:
                        discovery_output = json.loads(json_match.group(1))
                        logger.info("Successfully extracted JSON using regex")
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON extracted with regex")
            
            if not discovery_output:
                logger.warning("All attempts to parse discovery output failed")
                # Save the raw output for debugging
                debug_dir = os.path.join(self.file_manager.run_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)
                with open(os.path.join(debug_dir, "discovery_raw_output.txt"), "w") as f:
                    f.write(task_output.raw)
                return
            
            # Save the discovery data
            self.results["discovery"] = discovery_output
            
            # Extract family offices list - handle different possible structures
            family_offices = []
            if isinstance(discovery_output, dict):
                if "family_offices" in discovery_output:
                    family_offices = discovery_output["family_offices"]
                elif "results" in discovery_output:
                    family_offices = discovery_output["results"]
            elif isinstance(discovery_output, list):
                family_offices = discovery_output
                
                # If we got a list directly, wrap it in a dict for consistency
                discovery_output = {"family_offices": family_offices}
                self.results["discovery"] = discovery_output
            
            self.counts["discovery"] = len(family_offices)
            
            # Save as JSON
            json_path = self.file_manager.save_json(discovery_output, "1_family_offices_list.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
            
            # Format and save as CSV
            flattened_data = self.data_processor.format_discovery_for_csv(family_offices)
            discovery_fieldnames = ["name", "url", "location", "estimated_aum", "investment_focus", "aum_evidence", "confidence_score"]
            csv_path = self.file_manager.save_csv(flattened_data, "1_family_offices_list.csv", discovery_fieldnames)
            if csv_path:
                self.generated_files.append(os.path.basename(csv_path))
                
        except Exception as e:
            logger.error(f"Error processing discovery results: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def process_profile_output(self, task_output):
        """Process profile scraper task output"""
        try:
            # Clean the JSON output by removing any code block wrapper
            cleaned_output = self.json_processor.clean_json_output(task_output.raw)
            
            # Try to parse the JSON
            profile_output = self.json_processor.parse_json(cleaned_output)
            
            if not profile_output:
                logger.warning("Failed to parse profile output, trying alternative parsing")
                # Try to extract JSON from the text using regex
                json_pattern = r'({[\s\S]*})'
                json_match = re.search(json_pattern, task_output.raw)
                if json_match:
                    try:
                        profile_output = json.loads(json_match.group(1))
                        logger.info("Successfully extracted JSON using regex")
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON extracted with regex")
            
            if not profile_output:
                logger.warning("All attempts to parse profile output failed")
                # Save the raw output for debugging
                debug_dir = os.path.join(self.file_manager.run_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)
                with open(os.path.join(debug_dir, "profile_raw_output.txt"), "w") as f:
                    f.write(task_output.raw)
                return
            
            # Extract profile data
            profiles = []
            if isinstance(profile_output, dict):
                if "family_offices" in profile_output:
                    profiles = profile_output["family_offices"]
                elif "profiles" in profile_output:
                    profiles = profile_output["profiles"]
                elif "family_office_profiles" in profile_output:
                    profiles = profile_output["family_office_profiles"]
            elif isinstance(profile_output, list):
                profiles = profile_output
                
            self.results["profiles"] = profile_output
            self.counts["profiles"] = len(profiles)
            
            # Save as JSON
            json_path = self.file_manager.save_json(profile_output, "2_family_offices_profiles.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
            
            # Format and save as CSV
            flattened_profiles = self.data_processor.format_profiles_for_csv(profiles)
            
            # Use all available fields for the CSV
            profile_fieldnames = [
                "name", "url", "location", "address", "phone", "email", 
                "team_members", "aum", "aum_evidence", "investment_focus", 
                "investment_philosophy", "geographic_preferences", "typical_investment_size",
                "founding_year", "investment_types", "completeness_score"
            ]
            
            csv_path = self.file_manager.save_csv(flattened_profiles, "2_family_offices_profiles.csv", profile_fieldnames)
            if csv_path:
                self.generated_files.append(os.path.basename(csv_path))
                
        except Exception as e:
            logger.error(f"Error processing profile results: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def process_news_output(self, task_output):
        """Process news scraper task output"""
        try:
            # Clean the JSON output by removing any code block wrapper
            cleaned_output = self.json_processor.clean_json_output(task_output.raw)
            
            # Try to parse the JSON
            news_output = self.json_processor.parse_json(cleaned_output)
            
            if not news_output:
                logger.warning("Failed to parse news output")
                return
            
            # Save the news data
            self.results["news"] = news_output
            
            # Extract news data
            news_data = []
            if isinstance(news_output, dict):
                if "family_offices" in news_output:
                    news_data = news_output["family_offices"]
                elif "news" in news_output:
                    news_data = news_output["news"]
            elif isinstance(news_output, list):
                news_data = news_output
                
            self.counts["news"] = len(news_data)
            
            # Save as JSON
            json_path = self.file_manager.save_json(news_output, "3_family_offices_news.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
            
            # Format and save as CSV
            flattened_news = self.data_processor.format_news_for_csv(news_data)
            news_fieldnames = ["name", "activity_date", "activity_headline", "activity_description", 
                              "activity_source", "activity_url", "activity_type", "full_text",
                              "strategy_insights", "leadership_changes", "news_presence_score"]
            csv_path = self.file_manager.save_csv(flattened_news, "3_family_offices_news.csv", news_fieldnames)
            if csv_path:
                self.generated_files.append(os.path.basename(csv_path))
                
        except Exception as e:
            logger.error(f"Error processing news results: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def save_combined_results(self):
        """Save combined results from all agents"""
        try:
            combined_data = {
                "run_info": {
                    "date": self.file_manager.current_date,
                    "run_number": self.file_manager.run_number,
                    "timestamp": self.file_manager.current_datetime
                },
                "discovery": self.results["discovery"],
                "profiles": self.results["profiles"],
                "news": self.results["news"]
            }
            
            json_path = self.file_manager.save_json(combined_data, "4_combined_results.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
            
            # Save metadata about the run
            metadata = {
                "run_date": self.file_manager.current_date,
                "run_time": self.file_manager.current_datetime,
                "run_number": self.file_manager.run_number,
                "counts": self.counts,
                "files_generated": self.generated_files
            }
            
            self.file_manager.save_json(metadata, "run_metadata.json")
            
        except Exception as e:
            logger.error(f"Error saving combined results: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def print_summary(self):
        """Print a summary of the results"""
        try:
            print("\n==========================================")
            print("CHICAGO AREA FAMILY OFFICE FINDER ($100M+ AUM)")
            print("==========================================")
            print(f"Discovered {self.counts['discovery']} family offices within 300 miles of Chicago with estimated AUM of $100M+")
            print(f"Run date: {self.file_manager.current_date}, Run #: {self.file_manager.run_number}")
            print(f"All results saved to: {self.file_manager.run_dir}")
            print("==========================================")
            print("Files generated:")
            
            for i, file in enumerate(self.generated_files, 1):
                print(f"{i}. {file}")
                
            print("==========================================\n")
            
            # Print a preview of discovered offices
            if self.results["discovery"] and "family_offices" in self.results["discovery"]:
                discovery_data = self.results["discovery"]["family_offices"]
                preview_count = min(3, len(discovery_data))
                if preview_count > 0:
                    print("Preview of discovered high-AUM family offices:")
                    for i, office in enumerate(discovery_data[:preview_count]):
                        aum = office.get('aum_estimate', office.get('estimated_aum', 'AUM not specified'))
                        print(f"{i+1}. {office.get('name')} - AUM: {aum} - {office.get('url', 'No URL found')}")
                    print()
                    
        except Exception as e:
            logger.error(f"Error printing summary: {e}")

def run():
    """
    Run the Family Office Finder crew to discover family offices in a 300-mile radius of Chicago.
    """
    try:
        # Initialize processing components before crew execution
        file_manager = FileManager()
        json_processor = JsonProcessor()
        data_processor = DataProcessor()
        results_processor = ResultsProcessor(file_manager, json_processor, data_processor)
        
        # Initialize the crew
        crew_instance = FamilyOfficeFinderCrew()
        crew = crew_instance.crew()
        
        # Debug the task configurations before execution
        logger.info("Task configurations before execution:")
        for i, task in enumerate(crew.tasks):
            logger.info(f"Task {i+1}: {task.description[:100]}...")
        
        # Run the crew with retry logic for rate limit errors
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Run the discovery agent
                logger.info("Running discovery agent...")
                discovery_agent = crew_instance.family_office_discovery_agent()
                discovery_task = crew_instance.discovery_task()
                discovery_result = discovery_agent.execute_task(discovery_task)
                
                # Create a TaskOutput-like object
                class MockTaskOutput:
                    def __init__(self, raw):
                        self.raw = raw
                
                # Process the discovery output
                mock_output = MockTaskOutput(discovery_result)
                results_processor.process_discovery_output(mock_output)
                
                # Save the raw discovery output for debugging
                debug_dir = os.path.join(file_manager.run_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)
                with open(os.path.join(debug_dir, "discovery_agent_raw_output.txt"), "w") as f:
                    f.write(discovery_result)
                
                # Add a delay to avoid rate limits
                time.sleep(random.uniform(5, 10))
                
                # Check if discovery data was processed successfully
                if not results_processor.results["discovery"]:
                    logger.error("Discovery data processing failed, attempting to parse raw output")
                    try:
                        # Try to extract JSON directly from the raw output
                        json_pattern = r'({[\s\S]*})'
                        json_match = re.search(json_pattern, discovery_result)
                        if json_match:
                            discovery_json = json_match.group(1)
                            discovery_data = json.loads(discovery_json)
                            results_processor.results["discovery"] = discovery_data
                            
                            # Extract family offices
                            if "family_offices" in discovery_data:
                                family_offices = discovery_data["family_offices"]
                            elif isinstance(discovery_data, list):
                                family_offices = discovery_data
                                discovery_data = {"family_offices": family_offices}
                                results_processor.results["discovery"] = discovery_data
                            
                            logger.info(f"Successfully extracted {len(family_offices)} family offices from raw output")
                    except Exception as e:
                        logger.error(f"Failed to extract discovery data from raw output: {e}")
                
                # Run the profile agent if discovery was successful
                discovery_data = None
                if results_processor.results["discovery"]:
                    if "family_offices" in results_processor.results["discovery"]:
                        discovery_data = results_processor.results["discovery"]["family_offices"]
                    elif isinstance(results_processor.results["discovery"], list):
                        discovery_data = results_processor.results["discovery"]
                
                if discovery_data:
                    # Create a modified profile scraper task with explicit input
                    profile_task = crew_instance.profile_scraper_task()
                    context = {"discovered_offices": discovery_data}
                    
                    # Execute profile task directly
                    logger.info(f"Executing profile task with explicit context...")
                    profile_agent = crew_instance.family_office_profile_agent()
                    profile_result = profile_agent.execute_task(profile_task, context=context)
                    
                    # Process the manually executed profile task
                    mock_output = MockTaskOutput(profile_result)
                    results_processor.process_profile_output(mock_output)
                    
                    # Save the profile output to a file for debugging
                    debug_dir = os.path.join(file_manager.run_dir, "debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    with open(os.path.join(debug_dir, "profile_agent_raw_output.txt"), "w") as f:
                        f.write(profile_result)
                    
                    # Add a delay to avoid rate limits
                    time.sleep(random.uniform(10, 15))
                else:
                    logger.error("Could not find discovery data to pass to profile agent")
                
                # For news agent, use discovery data directly
                if results_processor.results["discovery"]:
                    discovery_data = None
                    if "family_offices" in results_processor.results["discovery"]:
                        discovery_data = results_processor.results["discovery"]["family_offices"]
                    elif "family_office_profiles" in results_processor.results["discovery"]:
                        discovery_data = results_processor.results["discovery"]["family_office_profiles"]
                    
                    if discovery_data:
                        # Create a modified news scraper task with explicit input
                        news_task = crew_instance.news_scraper_task()
                        context = {"profiled_offices": discovery_data}
                        
                        # Execute news task directly
                        logger.info(f"Executing news task with discovery data...")
                        news_agent = crew_instance.family_office_news_agent()
                        news_result = news_agent.execute_task(news_task, context=context)
                        
                        # Process the manually executed news task
                        mock_output = MockTaskOutput(news_result)
                        results_processor.process_news_output(mock_output)
                        
                        # Save the news output to a file for debugging
                        debug_dir = os.path.join(file_manager.run_dir, "debug")
                        os.makedirs(debug_dir, exist_ok=True)
                        with open(os.path.join(debug_dir, "news_agent_raw_output.txt"), "w") as f:
                            f.write(news_result)
                    else:
                        logger.error("Could not find discovery data to pass to news agent")
                else:
                    logger.error("No discovery data available for news agent")
                
                # Save combined results and print summary
                results_processor.save_combined_results()
                results_processor.print_summary()
                
                # If we got here, everything worked
                break
                
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    retry_count += 1
                    wait_time = 60 * retry_count  # Exponential backoff
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry {retry_count}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    # For non-rate-limit errors, log and re-raise
                    logger.error(f"Error running crew: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
        
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    run()