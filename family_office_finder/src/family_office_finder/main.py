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
        flattened_profiles = []
        
        for office in profiles:
            # Extract team members as a string
            team_members_str = ""
            if "team_members" in office and isinstance(office["team_members"], list):
                team_members = []
                for member in office["team_members"]:
                    if isinstance(member, dict):
                        name = member.get('name', '')
                        title = member.get('title', member.get('role', ''))
                        if name:
                            member_str = f"{name}: {title}" if title else name
                            team_members.append(member_str)
                team_members_str = "; ".join(team_members)
            
            # Extract contact information
            address = ""
            phone = ""
            email = ""
            if "contact_information" in office and isinstance(office["contact_information"], dict):
                address = office["contact_information"].get("address", "")
                phone = office["contact_information"].get("phone_number", "")
                email = office["contact_information"].get("email", "")
            
            # Create flattened profile
            flat_profile = {
                "name": office.get("name", ""),
                "website": office.get("url", office.get("website", "")),
                "address": address,
                "phone": phone,
                "email": email,
                "founding_year": office.get("founding_year", ""),
                "aum_estimate": office.get("aum_estimate", office.get("estimated_aum", "")),
                "aum_evidence": office.get("aum_evidence", ""),
                "investment_philosophy": office.get("investment_philosophy", ""),
                "target_sectors": office.get("target_sectors", office.get("investment_focus", "")),
                "geographic_preferences": office.get("geographic_preferences", ""),
                "typical_investment_size": office.get("typical_investment_size", ""),
                "investment_types": office.get("investment_types", ""),
                "team_members": team_members_str,
                "completeness_score": office.get("completeness_score", "")
            }
            flattened_profiles.append(flat_profile)
            
        return flattened_profiles
    
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
                    "strategy_insights": office_news.get("strategy_insights", ""),
                    "leadership_changes": office_news.get("leadership_changes", ""),
                    "news_presence_score": office_news.get("news_presence_score", "")
                }
                flattened_news.append(flat_news)
                
        return flattened_news

class ResultsProcessor:
    """Class for processing results from all agents"""
    
    def __init__(self, file_manager, json_processor, data_processor):
        self.file_manager = file_manager
        self.json_processor = json_processor
        self.data_processor = data_processor
        self.generated_files = []
        self.results = {
            "discovery": None,
            "profile": None,
            "news": None
        }
        self.counts = {
            "discovery": 0,
            "profile": 0,
            "news": 0
        }
    
    def process_discovery_output(self, task_output):
        """Process the output from the discovery agent"""
        try:
            # Clean and parse JSON
            cleaned_output = self.json_processor.clean_json_output(task_output.raw)
            parsed_output = self.json_processor.parse_json(cleaned_output)
            
            if not parsed_output:
                logger.warning("Failed to parse discovery output")
                return
            
            # Standardize data structure
            discovery_data = self.data_processor.standardize_discovery_data(parsed_output)
            self.counts["discovery"] = len(discovery_data)
            
            # Create a standardized structure for consistent processing
            discovery_output = {"family_offices": discovery_data}
            self.results["discovery"] = discovery_output
            
            # Save as JSON
            json_path = self.file_manager.save_json(discovery_output, "1_family_offices_list.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
            
            # Format and save as CSV
            flattened_data = self.data_processor.format_discovery_for_csv(discovery_data)
            fieldnames = ["name", "url", "location", "estimated_aum", "investment_focus", "aum_evidence", "confidence_score"]
            csv_path = self.file_manager.save_csv(flattened_data, "1_family_offices_list.csv", fieldnames)
            if csv_path:
                self.generated_files.append(os.path.basename(csv_path))
                
        except Exception as e:
            logger.error(f"Error processing discovery results: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def process_profile_output(self, task_output):
        """Process the output from the profile agent"""
        try:
            # Clean and parse JSON
            cleaned_profile = self.json_processor.clean_json_output(task_output.raw)
            logger.info(f"Profile data snippet: {cleaned_profile[:200]}...")
            
            # Log the full raw output for debugging if it's not too long
            if len(task_output.raw) < 1000:
                logger.info(f"Full profile raw output: {task_output.raw}")
            
            # Check if the output is empty or just contains an empty structure
            if not cleaned_profile.strip() or cleaned_profile.strip() in ["{}", "[]", '{"family_offices":[]}']:
                logger.warning("Profile output is empty or contains empty structure")
                
                # If we have discovery results, create fallback profile data from discovery data
                if self.results["discovery"] and "family_offices" in self.results["discovery"]:
                    discovery_data = self.results["discovery"]["family_offices"]
                    logger.info(f"Creating fallback profile data from {len(discovery_data)} discovery records")
                    
                    # Create minimal profile data from discovery data
                    profile_data = []
                    for office in discovery_data:
                        profile = {
                            "name": office.get("name", ""),
                            "website": office.get("url", ""),
                            "location": office.get("location", ""),
                            "aum_estimate": office.get("estimated_aum", ""),
                            "aum_evidence": office.get("aum_evidence", ""),
                            "investment_philosophy": "",
                            "target_sectors": office.get("investment_focus", ""),
                            "geographic_preferences": "",
                            "typical_investment_size": "",
                            "investment_types": "",
                            "team_members": [],
                            "completeness_score": 3  # Low score since this is fallback data
                        }
                        profile_data.append(profile)
                    
                    logger.info(f"Created {len(profile_data)} fallback profile records")
                    profile_output = {"family_offices": profile_data}
                    self.results["profile"] = profile_output
                    self.counts["profile"] = len(profile_data)
                    return
                else:
                    logger.error("No discovery data available for fallback profile creation")
                    return
            
            parsed_output = self.json_processor.parse_json(cleaned_profile)
            
            if not parsed_output:
                logger.warning("Failed to parse profile output")
                
                # Attempt more aggressive parsing by looking for JSON structures
                try:
                    # Look for JSON arrays or objects in the text
                    object_pattern = r'\{[^{}]*\}'
                    array_pattern = r'\[[^\[\]]*\]'
                    
                    matches = re.findall(object_pattern, cleaned_profile)
                    if matches:
                        logger.info(f"Found {len(matches)} potential JSON objects in text")
                        for match in matches:
                            try:
                                parsed_output = json.loads(match)
                                logger.info("Successfully parsed a JSON object from text")
                                break
                            except:
                                continue
                    
                    if not parsed_output:
                        matches = re.findall(array_pattern, cleaned_profile)
                        if matches:
                            logger.info(f"Found {len(matches)} potential JSON arrays in text")
                            for match in matches:
                                try:
                                    parsed_output = json.loads(match)
                                    logger.info("Successfully parsed a JSON array from text")
                                    break
                                except:
                                    continue
                except Exception as e:
                    logger.error(f"Error in aggressive JSON parsing: {e}")
                
                if not parsed_output:
                    # If still no valid JSON, create a minimal fallback from discovery data
                    if self.results["discovery"] and "family_offices" in self.results["discovery"]:
                        discovery_data = self.results["discovery"]["family_offices"]
                        logger.info(f"Creating fallback profile data from {len(discovery_data)} discovery records")
                        
                        # Create minimal profile data from discovery data
                        profile_data = []
                        for office in discovery_data:
                            profile = {
                                "name": office.get("name", ""),
                                "website": office.get("url", ""),
                                "location": office.get("location", ""),
                                "aum_estimate": office.get("estimated_aum", ""),
                                "aum_evidence": office.get("aum_evidence", ""),
                                "investment_philosophy": "",
                                "target_sectors": office.get("investment_focus", ""),
                                "geographic_preferences": "",
                                "typical_investment_size": "",
                                "investment_types": "",
                                "team_members": [],
                                "completeness_score": 3  # Low score since this is fallback data
                            }
                            profile_data.append(profile)
                        
                        logger.info(f"Created {len(profile_data)} fallback profile records")
                        profile_output = {"family_offices": profile_data}
                        self.results["profile"] = profile_output
                        self.counts["profile"] = len(profile_data)
                        return
                    else:
                        return
            
            # Standardize data structure
            profile_data = []
            if isinstance(parsed_output, dict):
                if "family_offices" in parsed_output:
                    profile_data = parsed_output["family_offices"]
                elif "profiles" in parsed_output:
                    profile_data = parsed_output["profiles"]
            elif isinstance(parsed_output, list):
                profile_data = parsed_output
            
            # If no profile data was found but we have discovery data, create fallback profiles
            if not profile_data and self.results["discovery"] and "family_offices" in self.results["discovery"]:
                discovery_data = self.results["discovery"]["family_offices"]
                logger.info(f"Creating fallback profile data from {len(discovery_data)} discovery records")
                
                # Create minimal profile data from discovery data
                for office in discovery_data:
                    profile = {
                        "name": office.get("name", ""),
                        "website": office.get("url", ""),
                        "location": office.get("location", ""),
                        "aum_estimate": office.get("estimated_aum", ""),
                        "aum_evidence": office.get("aum_evidence", ""),
                        "investment_philosophy": "",
                        "target_sectors": office.get("investment_focus", ""),
                        "geographic_preferences": "",
                        "typical_investment_size": "",
                        "investment_types": "",
                        "team_members": [],
                        "completeness_score": 3  # Low score since this is fallback data
                    }
                    profile_data.append(profile)
            
            self.counts["profile"] = len(profile_data)
            logger.info(f"Processed {len(profile_data)} profile records")
            
            # Create a standardized structure
            profile_output = {"family_offices": profile_data}
            self.results["profile"] = profile_output
            
            # Save as JSON
            json_path = self.file_manager.save_json(profile_output, "2_family_offices_profiles.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
            
            # Format and save as CSV
            flattened_profiles = self.data_processor.format_profiles_for_csv(profile_data)
            profile_fieldnames = ["name", "website", "address", "phone", "email", "founding_year", 
                              "aum_estimate", "aum_evidence", "investment_philosophy", 
                              "target_sectors", "geographic_preferences", "typical_investment_size", 
                              "investment_types", "team_members", "completeness_score"]
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
                "discovery_results": self.results["discovery"] if self.results["discovery"] else {},
                "profile_results": self.results["profile"] if self.results["profile"] else {},
                "news_results": self.results["news"] if self.results["news"] else {}
            }
            
            json_path = self.file_manager.save_json(combined_data, "4_combined_results.json")
            if json_path:
                self.generated_files.append(os.path.basename(json_path))
                
            # Save metadata about the run
            metadata = {
                "run_date": self.file_manager.current_date,
                "run_time": self.file_manager.current_datetime,
                "run_number": self.file_manager.run_number,
                "discovery_count": self.counts["discovery"],
                "profile_count": self.counts["profile"],
                "news_count": self.counts["news"],
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
        
        # Run the crew
        result = crew.kickoff()
        
        # Process the results from each agent
        if len(result.tasks_output) > 0:
            logger.info(f"Processing discovery output (length: {len(result.tasks_output[0].raw)})")
            results_processor.process_discovery_output(result.tasks_output[0])
            
        # For debugging, force reload the discovery task output for the profile task
        if len(result.tasks_output) > 0 and (len(result.tasks_output) <= 1 or not result.tasks_output[1].raw.strip()):
            logger.warning("Profile task output is empty or missing! Attempting to fix the issue...")
            
            # Get the discovery data to pass to the profile scraper task
            if results_processor.results["discovery"] and "family_offices" in results_processor.results["discovery"]:
                discovery_data = results_processor.results["discovery"]["family_offices"]
                
                # Create a modified profile scraper task with explicit input
                profile_task = crew_instance.profile_scraper_task()
                context = {"discovered_offices": discovery_data}
                
                # Execute profile task directly
                logger.info(f"Re-executing profile task with explicit context...")
                profile_agent = crew_instance.family_office_profile_agent()
                profile_result = profile_agent.execute_task(profile_task, context=context)
                
                # Create a TaskOutput-like object
                class MockTaskOutput:
                    def __init__(self, raw):
                        self.raw = raw
                
                # Process the manually executed profile task
                mock_output = MockTaskOutput(profile_result)
                results_processor.process_profile_output(mock_output)
            else:
                logger.error("Could not find discovery data to pass to profile agent")
        elif len(result.tasks_output) > 1:
            logger.info(f"Processing profile output (length: {len(result.tasks_output[1].raw)})")
            results_processor.process_profile_output(result.tasks_output[1])
        
        # For news agent, use discovery data directly if profile data is missing
        if len(result.tasks_output) > 2:
            logger.info(f"Processing news output (length: {len(result.tasks_output[2].raw)})")
            results_processor.process_news_output(result.tasks_output[2])
        else:
            logger.warning("News task output is missing! Attempting to fix the issue...")
            
            # Use discovery data directly for news agent
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
                    
                    # Create a TaskOutput-like object
                    class MockTaskOutput:
                        def __init__(self, raw):
                            self.raw = raw
                    
                    # Process the manually executed news task
                    mock_output = MockTaskOutput(news_result)
                    results_processor.process_news_output(mock_output)
                else:
                    logger.error("Could not find discovery data to pass to news agent")
            else:
                logger.error("No discovery data available for news agent")
        
        # Save combined results and print summary
        results_processor.save_combined_results()
        results_processor.print_summary()
        
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Print raw results for debugging
        if 'result' in locals() and hasattr(result, 'tasks_output'):
            logger.error("Raw task outputs for debugging:")
            for i, task_output in enumerate(result.tasks_output):
                logger.error(f"Task {i+1} output (first 500 chars):")
                logger.error(task_output.raw[:500] + "..." if len(task_output.raw) > 500 else task_output.raw)

if __name__ == "__main__":
    run()