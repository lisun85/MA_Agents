"""
Test module for media and news extraction functionality.

This test file focuses on diagnosing issues with the media extraction
from the branfordcastle.com directory.
"""

import os
import sys
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Set up logging with a more detailed format for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('media_extraction_test.log')
    ]
)
logger = logging.getLogger("test_media_extraction")

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Import required modules
from backend.aws.s3 import get_s3_client
from backend.summarizer.prompts import get_media_and_news_prompt
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MediaExtractionTester:
    """Test class for media and news extraction."""
    
    def __init__(self, debug_mode: bool = True):
        """
        Initialize the tester.
        
        Args:
            debug_mode: Whether to enable debug logging
        """
        self.debug_mode = debug_mode
        self.logger = logging.getLogger("MediaExtractionTester")
        
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
            
        # Get Google API key from environment variables
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required and not set in environment variables")
        
        # Initialize S3 client
        self.s3_client = get_s3_client()
        
        # Initialize the LLM with same configuration as Summarizer
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",  
            temperature=0,
            google_api_key=self.google_api_key
        )
        
        self.logger.info("MediaExtractionTester initialized")
        
    def retrieve_test_files(self, directory_name: str = "branfordcastle.com") -> Dict[str, str]:
        """
        Retrieve files from S3 to test media extraction.
        
        Args:
            directory_name: S3 directory to retrieve files from
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        self.logger.info(f"Retrieving files from {directory_name}")
        
        # List all files in the directory
        files_by_dir = self.s3_client.list_files_by_directory()
        
        if directory_name not in files_by_dir:
            self.logger.error(f"Directory {directory_name} not found in S3 bucket")
            return {}
        
        file_paths = files_by_dir[directory_name]
        self.logger.info(f"Found {len(file_paths)} files in directory {directory_name}")
        
        # Get content of all files
        contents = self.s3_client.get_files_content_by_directory(directory_name)
        
        if not contents:
            self.logger.error(f"No content found in directory {directory_name}")
            return {}
        
        # Create a dictionary mapping file paths to their contents
        file_content_map = {}
        for i, file_path in enumerate(file_paths):
            if i < len(contents):
                file_content_map[file_path] = contents[i]
        
        # Filter for media-related files for testing
        media_files = {}
        for file_path, content in file_content_map.items():
            filename = os.path.basename(file_path).lower()
            if "media" in filename or "news" in filename or "press" in filename or filename == "media-coverage.txt":
                media_files[file_path] = content
                self.logger.info(f"Including media-related file: {file_path}")
        
        # Always include portfolio.txt file since it's referenced as a source
        for file_path, content in file_content_map.items():
            if "portfolio.txt" in file_path:
                media_files[file_path] = content
                self.logger.info(f"Including portfolio file: {file_path}")
        
        # Add some index files or main content files
        for file_path, content in file_content_map.items():
            if "index.txt" in file_path or "about.txt" in file_path:
                media_files[file_path] = content
                self.logger.info(f"Including general content file: {file_path}")
        
        self.logger.info(f"Gathered {len(media_files)} files for testing")
        return media_files
    
    def test_extract_media(self, file_contents: Dict[str, str], firm_name: str = "Branford") -> Dict[str, Any]:
        """
        Test the media extraction functionality.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            firm_name: Name of the private equity firm
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"Testing media extraction for {firm_name}")
        
        results = {
            "total_files": len(file_contents),
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_media_items": 0,
            "errors": [],
            "files_processed": [],
            "media_items": []
        }
        
        # Process each file
        for file_path, content in file_contents.items():
            file_basename = os.path.basename(file_path)
            
            try:
                self.logger.info(f"Processing file: {file_basename}")
                
                # Special handling for media-coverage.txt file
                if "media-coverage.txt" in file_path.lower():
                    self.logger.info(f"Special handling for media-coverage.txt")
                    results["files_processed"].append(f"{file_basename} (special handling)")
                    
                    # Try direct extraction with special prompt
                    media_items = self._extract_from_media_coverage_file(file_path, content, firm_name)
                    
                    if media_items:
                        results["successful_extractions"] += 1
                        results["total_media_items"] += len(media_items)
                        results["media_items"].extend(media_items)
                        self.logger.info(f"Successfully extracted {len(media_items)} items from {file_basename} using special handling")
                    else:
                        self.logger.warning(f"Special handling extracted 0 items from {file_basename}")
                        results["failed_extractions"] += 1
                    
                    # Log the first few paragraphs of the file for diagnostic purposes
                    self._log_file_content_sample(file_path, content)
                    continue
                
                # For other files, use the regular prompt
                is_priority = any(k in file_basename.lower() for k in ["media", "news", "press", "release", "coverage"])
                
                prompt = get_media_and_news_prompt(
                    file_basename, 
                    content[:50000],
                    firm_name,
                    is_priority=is_priority
                )
                
                # Debug: log prompt for the first file
                if self.debug_mode and results["files_processed"] == []:
                    self.logger.debug(f"Example prompt for {file_basename}:\n{prompt[:300]}...")
                
                # Call the LLM
                response = self.llm.invoke(prompt)
                response_text = response.content
                
                # Debug: log response for diagnostics
                if self.debug_mode:
                    self.logger.debug(f"LLM response for {file_basename} (first 300 chars):\n{response_text[:300]}...")
                
                # Extract JSON from the response
                extracts = self._extract_json_from_response(response_text)
                
                if extracts and isinstance(extracts, list) and len(extracts) > 0:
                    valid_extracts = []
                    for extract in extracts:
                        if (isinstance(extract, dict) and 
                            "text" in extract and 
                            len(extract["text"]) > 10 and
                            extract["text"].lower() not in ["media", "news", "media section", "no media found"]):
                            
                            extract["source_file"] = file_basename
                            valid_extracts.append(extract)
                    
                    if valid_extracts:
                        results["successful_extractions"] += 1
                        results["total_media_items"] += len(valid_extracts)
                        results["media_items"].extend(valid_extracts)
                        results["files_processed"].append(file_basename)
                        self.logger.info(f"Successfully extracted {len(valid_extracts)} items from {file_basename}")
                    else:
                        results["failed_extractions"] += 1
                        results["files_processed"].append(f"{file_basename} (no valid content)")
                        self.logger.warning(f"No valid content extracted from {file_basename}")
                else:
                    results["failed_extractions"] += 1
                    results["files_processed"].append(f"{file_basename} (no extracts)")
                    self.logger.warning(f"No extracts found in {file_basename}")
            
            except Exception as e:
                results["failed_extractions"] += 1
                results["errors"].append(f"Error processing {file_basename}: {str(e)}")
                self.logger.error(f"Error processing {file_basename}: {str(e)}", exc_info=True)
        
        # Log summary of results
        self.logger.info(f"Media extraction test summary:")
        self.logger.info(f"  Total files processed: {results['total_files']}")
        self.logger.info(f"  Successful extractions: {results['successful_extractions']}")
        self.logger.info(f"  Failed extractions: {results['failed_extractions']}")
        self.logger.info(f"  Total media items extracted: {results['total_media_items']}")
        
        return results
    
    def _extract_from_media_coverage_file(self, file_path: str, content: str, firm_name: str) -> List[Dict[str, Any]]:
        """
        Extract media content from media-coverage.txt with specialized handling.
        
        Args:
            file_path: Path to the file
            content: File content
            firm_name: Name of the firm
        
        Returns:
            List of extracted media items
        """
        file_basename = os.path.basename(file_path)
        extracts = []
        
        # Try a series of increasingly aggressive extraction methods
        
        # Method 1: Specialized direct extraction with LLM
        try:
            self.logger.info("Trying specialized LLM extraction for media-coverage.txt")
            
            # Create a specialized prompt for media-coverage.txt
            specialized_prompt = f"""
            The following content is from {file_basename}, which contains media coverage, news articles, 
            and press releases about {firm_name}. Your task is to extract ALL news items and press releases.
            
            CRITICAL INSTRUCTIONS:
            1. This file is THE PRIMARY SOURCE of media and news content - extract EVERYTHING
            2. Extract each separate news item, press release, or announcement as an individual entry
            3. Include dates, headlines, and full text of each news item
            4. Do not skip any news items or announcements
            5. Return ALL media/news content, even if it seems minor
            
            Format each extract as a JSON object with:
            - "text": The full text of the news item or press release
            - "location": "Media coverage file"
            
            Combine all extracts into a JSON array.
            
            Content:
            {content[:50000]}
            """
            
            response = self.llm.invoke(specialized_prompt)
            specialized_extracts = self._extract_json_from_response(response.content)
            
            if specialized_extracts and isinstance(specialized_extracts, list) and len(specialized_extracts) > 0:
                self.logger.info(f"Specialized LLM extraction successful - found {len(specialized_extracts)} items")
                for extract in specialized_extracts:
                    if isinstance(extract, dict) and "text" in extract and len(extract["text"]) > 10:
                        extract["source_file"] = file_basename
                        extracts.append(extract)
                
                # If we found extracts, return them
                if extracts:
                    return extracts
            else:
                self.logger.warning("Specialized LLM extraction failed or returned no results")
        
        except Exception as e:
            self.logger.error(f"Error in specialized LLM extraction: {str(e)}")
        
        # Method 2: Direct content extraction with pattern matching
        try:
            self.logger.info("Trying pattern-based extraction for media-coverage.txt")
            
            # Look for common pattern in press releases - date formats
            date_pattern = re.compile(r'(?:\n|^)((?:\d{1,2}/\d{1,2}/\d{2,4}|[A-Z][a-z]+ \d{1,2},? \d{4}))', re.MULTILINE)
            date_matches = list(date_pattern.finditer(content))
            
            if date_matches:
                self.logger.info(f"Found {len(date_matches)} potential date markers")
                
                # Extract sections between dates
                for i, match in enumerate(date_matches):
                    start_pos = match.start()
                    
                    # Determine end position (next date or end of file)
                    if i < len(date_matches) - 1:
                        end_pos = date_matches[i + 1].start()
                    else:
                        end_pos = len(content)
                    
                    # Extract the section including the date
                    section = content[start_pos:end_pos].strip()
                    
                    if len(section) > 30:  # Minimum reasonable length for a news item
                        extracts.append({
                            "text": section,
                            "location": f"Media coverage file (date-based extraction)",
                            "source_file": file_basename
                        })
                
                if extracts:
                    self.logger.info(f"Date-based extraction found {len(extracts)} potential news items")
                    return extracts
            else:
                self.logger.warning("No date patterns found in content")
        
        except Exception as e:
            self.logger.error(f"Error in date-based extraction: {str(e)}")
        
        # Method 3: Paragraph-based extraction
        try:
            self.logger.info("Trying paragraph-based extraction for media-coverage.txt")
            
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
            
            for paragraph in paragraphs:
                if len(paragraph) > 100 and len(paragraph) < 2000:
                    # Look for news indicators in the paragraph
                    news_indicators = ["announce", "release", "today", "report", "acqui", "launch", "complete"]
                    if any(indicator in paragraph.lower() for indicator in news_indicators):
                        extracts.append({
                            "text": paragraph,
                            "location": "Media coverage file (paragraph extraction)",
                            "source_file": file_basename
                        })
            
            if extracts:
                self.logger.info(f"Paragraph-based extraction found {len(extracts)} potential news items")
                return extracts
            else:
                self.logger.warning("No suitable paragraphs found")
        
        except Exception as e:
            self.logger.error(f"Error in paragraph-based extraction: {str(e)}")
        
        # Method 4: Last resort - direct content extraction
        try:
            self.logger.info("Using direct content extraction as last resort")
            
            # Split the content into manageable chunks
            chunk_size = 1000  # Reasonable size for a news item
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) > 50:
                    extracts.append({
                        "text": chunk,
                        "location": f"Media coverage chunk {i+1}",
                        "source_file": file_basename
                    })
            
            if extracts:
                self.logger.info(f"Direct content extraction found {len(extracts)} chunks")
                return extracts
        
        except Exception as e:
            self.logger.error(f"Error in direct content extraction: {str(e)}")
        
        self.logger.error("All extraction methods failed for media-coverage.txt")
        return []
    
    def _extract_json_from_response(self, response_text: str) -> Any:
        """
        Extract JSON from LLM response text.
        
        Args:
            response_text: Response text from LLM
            
        Returns:
            Parsed JSON object or None
        """
        try:
            # Try to find a JSON array in the response
            match = re.search(r'(\[\s*\{.*\}\s*\])', response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                else:
                    # No JSON found
                    self.logger.warning(f"No JSON array found in response")
                    return None
            
            # Parse the JSON
            result = json.loads(json_str)
            self.logger.debug(f"Successfully parsed JSON with {len(result) if isinstance(result, list) else 'N/A'} items")
            return result
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            self.logger.debug(f"Problematic JSON: {response_text[:200]}...")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting JSON: {str(e)}")
            return None
    
    def _log_file_content_sample(self, file_path: str, content: str):
        """
        Log a sample of file content for diagnostic purposes.
        
        Args:
            file_path: Path to the file
            content: File content
        """
        if not self.debug_mode:
            return
            
        file_basename = os.path.basename(file_path)
        self.logger.debug(f"Content sample from {file_basename}:")
        
        # Get first few paragraphs
        paragraphs = content.split('\n\n')
        sample = '\n\n'.join(paragraphs[:3])
        
        # Limit sample size
        if len(sample) > 500:
            sample = sample[:500] + "..."
            
        self.logger.debug(sample)
    
    def save_results(self, results: Dict[str, Any], filename: str = "media_extraction_results.json"):
        """
        Save test results to a file.
        
        Args:
            results: Test results dictionary
            filename: Name of the file to save results to
        """
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
    
    def print_media_items(self, results: Dict[str, Any]):
        """
        Print extracted media items in a readable format.
        
        Args:
            results: Test results dictionary
        """
        media_items = results.get("media_items", [])
        
        if not media_items:
            print("No media items extracted.")
            return
        
        print(f"\n===== EXTRACTED MEDIA ITEMS ({len(media_items)}) =====\n")
        
        for i, item in enumerate(media_items):
            print(f"Item {i+1}:")
            print(f"Source: {item.get('source_file', 'Unknown')}")
            print(f"Location: {item.get('location', 'Unknown')}")
            
            text = item.get('text', '')
            if len(text) > 200:
                text = text[:200] + "..."
                
            print(f"Text: {text}")
            print("-" * 50)


def main():
    """Main entry point for the test script."""
    try:
        # Create the tester
        tester = MediaExtractionTester(debug_mode=True)
        
        # Retrieve test files
        file_contents = tester.retrieve_test_files("branfordcastle.com")
        
        if not file_contents:
            print("Error: No test files retrieved")
            return 1
        
        # Test media extraction
        results = tester.test_extract_media(file_contents)
        
        # Save results
        tester.save_results(results)
        
        # Print media items
        tester.print_media_items(results)
        
        return 0
    
    except Exception as e:
        print(f"Error in test script: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 