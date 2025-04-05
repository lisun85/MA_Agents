"""
Targeted test module for media extraction focused on portfolio.txt.

This test specifically analyzes the portfolio.txt file from branfordcastle.com
to identify why media extraction may be failing.
"""

import os
import sys
import logging
import json
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Set up logging with a detailed format for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('portfolio_media_extraction.log')
    ]
)
logger = logging.getLogger("test_media2")

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Set default output directory to the summarizer/output folder
default_output_dir = current_dir / "output"
os.makedirs(default_output_dir, exist_ok=True)

# Import required modules
from backend.aws.s3 import get_s3_client
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the exact prompt definition from prompts.py
def get_media_and_news_prompt(source_file: str, content: str, firm_name: str = None, is_priority: bool = False) -> str:
    """
    Generate the prompt for extracting media mentions and news articles.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm
        is_priority: Whether this is a priority file that likely contains media content
        
    Returns:
        Formatted prompt string
    """
    if not firm_name:
        firm_name = "the private equity firm"
    
    # More specific instructions for priority files
    priority_instructions = """
    This file is likely to contain media content. Look carefully for:
    - Press releases or announcements (often containing dates)
    - Deal announcements (acquisitions, investments, exits)
    - Awards or recognition
    - Media mentions or quotes from news sources
    - Annual reports or investor communications
    """ if is_priority else ""
    
    return f"""
    Please extract verbatim text describing media mentions, news articles, or press releases about {firm_name} from the following file: {source_file}.
    
    {priority_instructions}
    
    IMPORTANT INSTRUCTIONS:
    1. Only extract DIRECT QUOTES from the text about:
       - Media coverage and press mentions
       - News articles and press releases
       - Deal announcements (acquisitions, investments)
       - Company awards and recognition
       - Major events and milestones
       - Executive appointments and leadership changes
    
    2. Look for content that has news value, often indicated by:
       - Dates or time references
       - Quotes from executives
       - Mentions of transactions, financial figures, or business outcomes
       - References to industry recognition or awards
    
    3. Preserve the exact wording from the text - copy and paste the relevant passages
    4. DO NOT use general labels like "MEDIA" - extract the actual text content
    5. DO NOT summarize or paraphrase - only provide direct quotes
    6. Each extract should be substantive content about specific media mentions or news items
    7. If no relevant content is found, return an empty JSON array
    8. DO NOT include general website navigation text or headers that don't contain actual news content
    
    For each extract, provide:
    - "text": The exact verbatim text from the document (NOT placeholder text like "MEDIA")
    - "location": A brief description of where in the document this appears (e.g., "News section")
    
    The format should be:
    [
      {{"text": "Verbatim text about media mention...", "location": "News page"}},
      {{"text": "Another verbatim extract about press release...", "location": "Media section"}}
    ]
    
    ONLY return the JSON array.
    
    Here's the text to analyze:
    
    {content}
    """


class PortfolioMediaTest:
    """Test class for media extraction from portfolio.txt."""
    
    def __init__(self, debug_mode: bool = True):
        """
        Initialize the tester.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.logger = logging.getLogger("PortfolioMediaTest")
        
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            
        # Get Google API key from environment variables
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required and not set in environment variables")
        
        # Initialize S3 client - using the same approach as in summarizer.py
        self.s3_client = get_s3_client()
        
        # Initialize the LLM with same configuration as Summarizer
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",  
            temperature=0,
            google_api_key=self.google_api_key
        )
        
        self.logger.info("PortfolioMediaTest initialized")
    
    def retrieve_portfolio_file(self, directory_name: str = "branfordcastle.com") -> Dict[str, str]:
        """
        Retrieve only the portfolio.txt file from the specified directory.
        
        Args:
            directory_name: S3 directory to retrieve files from
            
        Returns:
            Dictionary mapping file path to content, or empty dict if not found
        """
        self.logger.info(f"Retrieving portfolio.txt from {directory_name}")
        
        # List all files in the directory
        files_by_dir = self.s3_client.list_files_by_directory()
        
        if directory_name not in files_by_dir:
            self.logger.error(f"Directory {directory_name} not found in S3 bucket")
            return {}
        
        file_paths = files_by_dir[directory_name]
        portfolio_path = None
        
        # Find the portfolio.txt file path
        for path in file_paths:
            if path.lower().endswith("portfolio.txt"):
                portfolio_path = path
                self.logger.info(f"Found portfolio file at: {portfolio_path}")
                break
        
        if not portfolio_path:
            self.logger.error("portfolio.txt not found in directory")
            return {}
            
        # Get content of the portfolio.txt file
        portfolio_content = self.s3_client.get_file_content(portfolio_path)
        
        if not portfolio_content:
            self.logger.error(f"Failed to retrieve content for {portfolio_path}")
            return {}
            
        self.logger.info(f"Retrieved portfolio.txt with {len(portfolio_content)} characters")
        return {portfolio_path: portfolio_content}
        
    def retrieve_all_media_files(self, directory_name: str = "branfordcastle.com") -> Dict[str, str]:
        """
        Retrieve all potential media files from the specified directory.
        
        Args:
            directory_name: S3 directory to retrieve files from
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        self.logger.info(f"Retrieving all media-related files from {directory_name}")
        
        # List all files in the directory
        files_by_dir = self.s3_client.list_files_by_directory()
        
        if directory_name not in files_by_dir:
            self.logger.error(f"Directory {directory_name} not found in S3 bucket")
            return {}
        
        file_paths = files_by_dir[directory_name]
        self.logger.info(f"Found {len(file_paths)} files in directory {directory_name}")
        
        # Identify potential media files
        media_related_paths = []
        for path in file_paths:
            filename = os.path.basename(path).lower()
            if any(term in filename for term in ["media", "news", "press", "coverage", "portfolio"]):
                media_related_paths.append(path)
                self.logger.info(f"Including potential media file: {path}")
        
        if not media_related_paths:
            self.logger.warning("No media-related files found")
            # Include at least the portfolio file as a fallback
            for path in file_paths:
                if path.lower().endswith("portfolio.txt"):
                    media_related_paths.append(path)
                    self.logger.info(f"Including portfolio file as fallback: {path}")
        
        # Get content of the media files
        media_files = {}
        for path in media_related_paths:
            content = self.s3_client.get_file_content(path)
            if content:
                media_files[path] = content
                self.logger.info(f"Retrieved {os.path.basename(path)} with {len(content)} characters")
            else:
                self.logger.error(f"Failed to retrieve content for {path}")
        
        return media_files
    
    def test_media_extraction(self, file_contents: Dict[str, str], firm_name: str = "Branford Castle") -> Dict[str, Any]:
        """
        Test the media extraction functionality on the portfolio file.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            firm_name: Name of the private equity firm
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"Testing media extraction for {firm_name} from {len(file_contents)} files")
        
        results = {
            "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "firm_name": firm_name,
            "files_tested": [],
            "media_items": [],
            "raw_extracts": [],
            "errors": []
        }
        
        # Process each file
        for file_path, content in file_contents.items():
            file_basename = os.path.basename(file_path)
            
            try:
                self.logger.info(f"Processing file: {file_basename}")
                
                # Record the file being tested
                results["files_tested"].append({
                    "path": file_path,
                    "basename": file_basename,
                    "size_bytes": len(content),
                    "size_chars": len(content)
                })
                
                # Generate the prompt - using the exact same logic from summarizer.py
                is_priority = any(term in file_basename.lower() for term in ["media", "news", "press", "coverage"])
                
                # Use the imported get_media_and_news_prompt function
                prompt = get_media_and_news_prompt(
                    file_basename, 
                    content, 
                    firm_name,
                    is_priority=is_priority
                )
                
                # Log the prompt for debugging
                if self.debug_mode:
                    self.logger.debug(f"Generated prompt for {file_basename}:\n{prompt[:500]}...")
                
                # Call the LLM
                self.logger.info(f"Calling LLM with prompt for {file_basename}")
                response = self.llm.invoke(prompt)
                response_text = response.content
                
                # Log the raw response
                if self.debug_mode:
                    self.logger.debug(f"Raw LLM response for {file_basename}:\n{response_text[:500]}...")
                
                # Record the raw response for analysis
                results["raw_extracts"].append({
                    "file": file_basename,
                    "response": response_text
                })
                
                # Process the response - using the same extraction logic as in summarizer.py
                try:
                    extracts = self._extract_json_from_response(response_text)
                    
                    if extracts and isinstance(extracts, list):
                        valid_extracts = []
                        
                        for extract in extracts:
                            # Validate each extract using the exact same logic as in summarizer.py
                            if isinstance(extract, dict) and "text" in extract:
                                extract_text = extract["text"]
                                
                                # Check for placeholder text - an issue observed in summarizer
                                if (len(extract_text) > 5 and 
                                    extract_text.lower() not in ["media", "news", "press", "media section", "no media content found"]):
                                    
                                    # Add source information
                                    extract["source_file"] = file_basename
                                    valid_extracts.append(extract)
                                else:
                                    self.logger.warning(f"Skipping placeholder extract: {extract_text}")
                        
                        # Add the valid extracts to our results
                        if valid_extracts:
                            self.logger.info(f"Found {len(valid_extracts)} valid media items in {file_basename}")
                            results["media_items"].extend(valid_extracts)
                        else:
                            self.logger.warning(f"No valid media items found in {file_basename} despite LLM returning data")
                    else:
                        self.logger.warning(f"No extracts found in {file_basename}")
                
                except Exception as e:
                    self.logger.error(f"Error processing LLM response for {file_basename}: {str(e)}")
                    results["errors"].append({
                        "file": file_basename,
                        "error": f"Processing error: {str(e)}",
                        "response_sample": response_text[:200] if response_text else "None"
                    })
            
            except Exception as e:
                self.logger.error(f"Error extracting media from {file_basename}: {str(e)}", exc_info=True)
                results["errors"].append({
                    "file": file_basename,
                    "error": f"Extraction error: {str(e)}"
                })
        
        # Generate a summary for the results
        results["summary"] = {
            "total_files": len(file_contents),
            "files_processed": len(results["files_tested"]),
            "media_items_found": len(results["media_items"]),
            "error_count": len(results["errors"])
        }
        
        self.logger.info(f"Media extraction test completed. Found {len(results['media_items'])} media items from {len(file_contents)} files.")
        
        return results
    
    def _extract_json_from_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract JSON from LLM response text - using the same logic as in summarizer.py.
        
        Args:
            response_text: Response text from LLM
            
        Returns:
            Parsed JSON array or empty list
        """
        try:
            # First, check if the response contains a JSON array
            match = re.search(r'(\[\s*\{.*\}\s*\])', response_text, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                self.logger.debug("Found JSON array using regex")
            else:
                # Try to extract JSON based on brackets - same as summarizer.py
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    self.logger.debug("Found JSON array using bracket positions")
                else:
                    self.logger.warning("No JSON array found in response")
                    return []
            
            # Parse the JSON
            parsed_json = json.loads(json_str)
            
            # Validate it's a list as expected
            if isinstance(parsed_json, list):
                self.logger.info(f"Successfully parsed JSON with {len(parsed_json)} items")
                return parsed_json
            else:
                self.logger.warning("Parsed JSON is not a list as expected")
                return []
        
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON from response")
            self.logger.debug(f"Problematic text: {response_text[:500]}...")
            return []
        
        except Exception as e:
            self.logger.error(f"Unexpected error extracting JSON: {str(e)}")
            return []
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """
        Generate a readable report from test results.
        
        Args:
            results: Test results dictionary
            
        Returns:
            Formatted report string
        """
        # Generate a nicely formatted report
        report = []
        
        # Title and basic info
        report.append("=" * 80)
        report.append(f"MEDIA EXTRACTION TEST REPORT - {results['firm_name']}")
        report.append(f"Timestamp: {results['timestamp']}")
        report.append("=" * 80)
        
        # Summary section
        report.append("\nSUMMARY:")
        report.append("-" * 40)
        summary = results["summary"]
        report.append(f"Total files processed: {summary['total_files']}")
        report.append(f"Media items found: {summary['media_items_found']}")
        report.append(f"Error count: {summary['error_count']}")
        
        # Files section
        report.append("\nFILES PROCESSED:")
        report.append("-" * 40)
        for file in results["files_tested"]:
            report.append(f"- {file['basename']} ({file['size_chars']} characters)")
        
        # Media items section
        report.append("\nEXTRACTED MEDIA ITEMS:")
        report.append("-" * 40)
        
        if not results["media_items"]:
            report.append("No media items were extracted.")
        else:
            for i, item in enumerate(results["media_items"]):
                report.append(f"\nItem {i+1}:")
                report.append(f"Source: {item.get('source_file', 'Unknown')}")
                report.append(f"Location: {item.get('location', 'Unknown')}")
                
                # Format the text for readability
                text = item.get('text', '').strip()
                if text:
                    report.append("Text:")
                    report.append(f"\"{text}\"")
                else:
                    report.append("Text: [EMPTY]")
                
                report.append("-" * 40)
        
        # Errors section
        if results["errors"]:
            report.append("\nERRORS:")
            report.append("-" * 40)
            for i, error in enumerate(results["errors"]):
                report.append(f"{i+1}. File: {error.get('file', 'Unknown')}")
                report.append(f"   Error: {error.get('error', 'Unknown error')}")
                report.append("")
        
        # Analysis section - this is specific to this test
        report.append("\nANALYSIS:")
        report.append("-" * 40)
        
        # Analyze raw extracts for patterns in LLM responses
        raw_responses = [item["response"] for item in results.get("raw_extracts", [])]
        empty_arrays = sum(1 for r in raw_responses if "[]" in r)
        
        report.append(f"Files returning empty JSON arrays: {empty_arrays} of {len(raw_responses)}")
        
        # Look for common placeholder text patterns
        placeholder_patterns = ["MEDIA", "NEWS", "No relevant content found"]
        for pattern in placeholder_patterns:
            count = sum(1 for r in raw_responses if pattern in r)
            if count > 0:
                report.append(f"Responses containing '{pattern}': {count}")
        
        # Add diagnostic conclusion
        if results["media_items"]:
            report.append("\nCONCLUSION: Media items were successfully extracted.")
        else:
            report.append("\nCONCLUSION: No valid media items were extracted. Possible reasons:")
            report.append("1. The portfolio.txt file does not contain media-related content")
            report.append("2. The LLM is not recognizing media content in the text")
            report.append("3. The media content is in an unexpected format")
            report.append("4. The extraction prompt needs adjustment for this specific file type")
        
        # Recommendations
        report.append("\nRECOMMENDATIONS:")
        report.append("1. Check if media content is in other files specific to media coverage")
        report.append("2. Analyze the log file for detailed debugging information")
        report.append("3. Try modifying the prompt to be more specific about the types of media extracts expected")
        report.append("4. Manually review the content of media-related files to confirm if media content exists")
        
        return "\n".join(report)
    
    def save_report(self, report: str, results: Dict[str, Any], output_dir: str = None) -> None:
        """
        Save the report and results to files.
        
        Args:
            report: Formatted report string
            results: Test results dictionary
            output_dir: Directory to save files in (default: summarizer/output)
        """
        if output_dir is None:
            output_dir = default_output_dir
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filenames based on timestamp and firm name
        timestamp = results["timestamp"]
        safe_firm_name = results["firm_name"].replace(" ", "_").lower()
        
        report_filename = f"{safe_firm_name}_portfolio_media_test_{timestamp}.txt"
        json_filename = f"{safe_firm_name}_portfolio_media_test_{timestamp}.json"
        
        # Save the report
        report_path = os.path.join(output_dir, report_filename)
        with open(report_path, "w") as f:
            f.write(report)
        
        self.logger.info(f"Report saved to: {report_path}")
        
        # Save the full results as JSON
        json_path = os.path.join(output_dir, json_filename)
        with open(json_path, "w") as f:
            # Remove very large response texts to keep the JSON file manageable
            results_copy = results.copy()
            for extract in results_copy.get("raw_extracts", []):
                if "response" in extract and len(extract["response"]) > 1000:
                    extract["response"] = extract["response"][:1000] + "... [truncated]"
            
            json.dump(results_copy, f, indent=2)
        
        self.logger.info(f"Results saved as JSON to: {json_path}")


def main():
    """Main entry point for the test script."""
    try:
        print("Starting portfolio media extraction test...")
        
        # Create the tester
        tester = PortfolioMediaTest(debug_mode=True)
        
        # First, try to get only the portfolio.txt file
        portfolio_file = tester.retrieve_portfolio_file("branfordcastle.com")
        
        if not portfolio_file:
            print("WARNING: Portfolio.txt not found. Trying to retrieve all media-related files...")
            # Fallback: try to get all media-related files
            portfolio_file = tester.retrieve_all_media_files("branfordcastle.com")
        
        if not portfolio_file:
            print("ERROR: No files could be retrieved for testing.")
            return 1
        
        # Test the media extraction
        results = tester.test_media_extraction(portfolio_file)
        
        # Generate the report
        report = tester.generate_report(results)
        
        # Save the report and results
        tester.save_report(report, results)
        
        # Print a portion of the report to the console
        print("\n" + "=" * 80)
        print("TEST RESULTS PREVIEW:")
        print("=" * 80)
        print("\n".join(report.split("\n")[:20]))
        print("...")
        print(f"\nFull report saved to {default_output_dir}")
        
        return 0
    
    except Exception as e:
        print(f"Error in test script: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 