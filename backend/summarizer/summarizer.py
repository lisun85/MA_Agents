import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
import json
from datetime import datetime
import re
import asyncio
from backend.summarizer.parallel_extraction import ParallelExtractionManager
from transformers import AutoTokenizer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Import the S3 client
from backend.aws.s3 import get_s3_client
from langchain_google_genai import ChatGoogleGenerativeAI  # Changed to Google Gemini
from dotenv import load_dotenv
from backend.summarizer.prompts import (
    get_company_extraction_prompt, 
    get_connection_test_prompt, 
    get_investment_strategy_prompt,  # New consolidated prompt
    get_industry_focus_prompt, 
    get_industry_focus_summary_prompt, 
    get_geographic_focus_prompt, 
    get_geographic_focus_summary_prompt, 
    get_team_and_contacts_prompt, 
    get_media_and_news_prompt
)

# Load environment variables
load_dotenv()

# Get Google API key from environment variables
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables. Please add it to your .env file.")
    raise ValueError("GOOGLE_API_KEY is required and not set in environment.")

class Summarizer:
    """Agent that summarizes key information from S3 directory documents."""
    
    def __init__(self):
        """Initialize the summarizer with S3 client and LLM."""
        # Initialize logger as an instance attribute
        self.logger = logging.getLogger(__name__)
        
        self.s3_client = get_s3_client()
        
        # Initialize Google Gemini 2.0 Flash model (changed from 2.5 Pro)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",  # Changed from gemini-2.5-pro-exp-03-25
            temperature=0,
            google_api_key=google_api_key  # Explicitly pass the API key
        )
        
        # Test LLM connection
        self._test_llm_connection()
        
        # Initialize unprocessed_files list
        self.unprocessed_files = []
    
    def _test_llm_connection(self):
        """Test the LLM connection to verify API key is working."""
        try:
            test_prompt = get_connection_test_prompt()
            response = self.llm.invoke(test_prompt)
            self.logger.info(f"Google Gemini 2.0 Flash connection test: {response.content[:50]}...")
        except Exception as e:
            self.logger.error(f"LLM connection test failed: {str(e)}")
            self.logger.error("Check if your GOOGLE_API_KEY is correct in the .env file")
            # Continue execution to allow the program to run
    
    def summarize_directory(self, directory_name: str, use_parallel: bool = False) -> Dict[str, Any]:
        """
        Extract and summarize key information from a directory in S3.
        
        Args:
            directory_name: The name of the directory in S3 (e.g., "branfordcastle.com")
            use_parallel: Whether to use parallel extraction for faster processing
            
        Returns:
            Dict containing summary data and metadata
        """
        # Remove trailing slashes for consistency
        directory_name = directory_name.rstrip('/')
        
        self.logger.info(f"Summarizing content from directory: {directory_name}")
        
        # Step 1: List all files in the directory
        files_by_dir = self.s3_client.list_files_by_directory()
        
        if directory_name not in files_by_dir:
            self.logger.error(f"Directory '{directory_name}' not found in S3 bucket")
            return {
                "success": False,
                "error": f"Directory '{directory_name}' not found in S3 bucket",
                "directory": directory_name,
                "summary": {}
            }
        
        file_paths = files_by_dir[directory_name]
        self.logger.info(f"Found {len(file_paths)} files in directory '{directory_name}'")
        
        # Step 2: Get content of all files
        contents = self.s3_client.get_files_content_by_directory(directory_name)
        
        if not contents:
            self.logger.error(f"No content found in directory '{directory_name}'")
            return {
                "success": False,
                "error": f"No content found in directory '{directory_name}'",
                "directory": directory_name,
                "summary": {}
            }
        
        self.logger.info(f"Retrieved content for {len(contents)} files")
        
        # Step 3: Create a dictionary mapping file paths to their contents
        file_content_map = {}
        for i, file_path in enumerate(file_paths):
            if i < len(contents):
                file_content_map[file_path] = contents[i]
        
        # Extract firm name early
        self.current_firm_name = self._extract_firm_name(directory_name, file_content_map)
        
        # Step 4: Extract information - either parallel or sequential
        if use_parallel:
            self.logger.info("Using parallel extraction")
            try:
                # Initialize the parallel extraction manager
                manager = ParallelExtractionManager(self)
                
                # Run parallel extraction asynchronously using asyncio
                loop = asyncio.get_event_loop()
                summary_result = loop.run_until_complete(
                    manager.run_parallel_extraction(file_content_map, directory_name)
                )
                
                # If parallel extraction succeeded, return the result
                if summary_result and summary_result.get("success", False):
                    self.logger.info(f"Parallel summarization complete. Found {len(summary_result['summary']['portfolio_companies'])} portfolio companies for {self.current_firm_name}.")
                    return summary_result
                    
                # Otherwise, fall back to sequential extraction
                self.logger.warning("Parallel extraction failed, falling back to sequential extraction")
            except Exception as e:
                self.logger.error(f"Error during parallel extraction: {str(e)}")
                self.logger.warning("Falling back to sequential extraction")
        
        # Sequential extraction (original implementation)
        self.logger.info("Using sequential extraction")
        
        # Step 4: Extract all sections
        self.logger.info("Extracting information from files...")
        
        # Extract portfolio companies (existing functionality)
        portfolio_companies = self._extract_portfolio_companies(file_content_map)
        
        # Extract combined investment strategy and criteria (replacing separate methods)
        investment_strategy = self._extract_investment_strategy(file_content_map)
        
        # Extract other sections
        industry_focus = self._extract_industry_focus(file_content_map)
        geographic_focus = self._extract_geographic_focus(file_content_map)
        team_and_contacts = self._extract_team_and_contacts(file_content_map)
        media_and_news = self._extract_media_and_news(file_content_map)
        
        # Step 5: Create the summary result
        summary_result = {
            "success": True,
            "directory": directory_name,
            "firm_name": self.current_firm_name,
            "file_count": len(contents),
            "summary": {
                "portfolio_companies": portfolio_companies,
                "investment_strategy": investment_strategy,
                "industry_focus": industry_focus,
                "geographic_focus": geographic_focus,
                "team_and_contacts": team_and_contacts,
                "media_and_news": media_and_news
            },
            "timestamp": self.get_timestamp()
        }
        
        self.logger.info(f"Summarization complete. Found {len(portfolio_companies)} portfolio companies for {self.current_firm_name}.")
        return summary_result
    
    def _extract_portfolio_companies(self, file_contents):
        """
        Extract portfolio companies from file contents using LLM only.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            List of company objects
        """
        all_companies = []
        portfolio_companies = []  # Companies extracted from portfolio.txt
        other_companies = []      # Companies extracted from other files
        
        # First, look for a dedicated portfolio file
        portfolio_files = [f for f in file_contents.keys() if "portfolio" in f.lower()]
        if portfolio_files:
            for portfolio_file in portfolio_files:
                # Use LLM extraction
                self.logger.info(f"Extracting from authoritative file: {portfolio_file}")
                companies = self._extract_companies_with_llm(file_contents[portfolio_file], portfolio_file, True, self.current_firm_name)
                
                # Set a higher confidence score and flag as from portfolio file
                for company in companies:
                    company['confidence_score'] = 0.95  # Higher confidence for portfolio file
                    company['from_portfolio_file'] = True
                    
                portfolio_companies.extend(companies)
                self.logger.info(f"Extracted {len(companies)} companies from portfolio file: {portfolio_file}")
        
        # Then process all other files
        for file_path, content in file_contents.items():
            # Skip if already processed as a portfolio file
            if "portfolio" in file_path.lower():
                continue
                
            # Use LLM extraction for each file
            companies = self._extract_companies_with_llm(content, file_path, False, self.current_firm_name)
            
            # Flag as from non-portfolio file
            for company in companies:
                company['from_portfolio_file'] = False
                
            other_companies.extend(companies)
        
        # Combine all companies, putting portfolio companies first
        all_companies = portfolio_companies + other_companies
        
        # If we found companies, deduplicate them
        if all_companies:
            all_companies = self._deduplicate_companies(all_companies)
        
        return all_companies
    
    def _extract_companies_with_llm(self, content: str, source_file: str, is_portfolio_file: bool, firm_name: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract company names from content.
        
        Args:
            content: The text content to analyze
            source_file: Source file path for reference
            is_portfolio_file: Whether this is a dedicated portfolio file
            firm_name: Name of the private equity firm
            
        Returns:
            List of company objects
        """
        # Set confidence score based on file type
        base_confidence = 0.9 if is_portfolio_file else 0.7
        
        # Truncate content to avoid token limits
        truncated_content = content[:50000]
        
        # Get the prompt from the prompts module, passing the firm name
        prompt = get_company_extraction_prompt(os.path.basename(source_file), truncated_content, firm_name)
        
        try:
            # Log file being processed
            self.logger.info(f"Processing file with LLM: {os.path.basename(source_file)}")
            
            # Call the LLM
            response = self.llm.invoke(prompt)
            
            # Extract JSON from the response
            response_text = response.content
            
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
                    # Log the error and return empty list
                    self.logger.error(f"Failed to extract JSON from LLM response for {os.path.basename(source_file)}")
                    self.logger.debug(f"LLM response start: {response_text[:200]}...")
                    self.unprocessed_files.append(os.path.basename(source_file))
                    return []
            
            # Try to parse the JSON
            try:
                extracted_companies = json.loads(json_str)
                
                # Check if we got a valid list
                if not isinstance(extracted_companies, list):
                    self.logger.error(f"LLM returned non-list JSON for {os.path.basename(source_file)}")
                    return []
                
                # Clean up and standardize company names and details
                companies = []
                for company in extracted_companies:
                    if isinstance(company, dict) and "name" in company:
                        # Clean up the company name - filter out URLs as company names
                        name = company["name"]
                        
                        # Skip if the name is likely an invalid or generic entry
                        if name.lower() in ["unknown", "none", "n/a", "no name provided", "not specified"]:
                            continue
                        
                        # Clean up description text
                        description = company.get("description", "No description available")
                        if len(description) > 200:
                            # Find the last complete sentence within 200 chars
                            last_period = description[:200].rfind('.')
                            if last_period > 0:
                                description = description[:last_period+1]
                            else:
                                description = description[:200] + "..."
                        
                        # Ensure website is in the details field, not the company name
                        details = company.get("details", "No additional details")
                        
                        # If name looks like a URL but details doesn't have a website field, add it
                        if (name.lower().endswith('.com') or name.lower().endswith('.net')) and "website:" not in details.lower():
                            # Generate proper company name from domain
                            proper_name = self._extract_company_name_from_url(name)
                            details = f"Website: {name}, {details}"
                            name = proper_name
                        
                        companies.append({
                            "name": name,
                            "description": description,
                            "details": details,
                            "source_file": os.path.basename(source_file),
                            "confidence_score": base_confidence,
                            "is_owned": company.get("is_owned", True),  # Default to True
                            "affiliate": company.get("affiliate", False)  # Default to False
                        })
                
                self.logger.info(f"LLM extracted {len(companies)} owned portfolio companies from {os.path.basename(source_file)}")
                return companies
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error for {os.path.basename(source_file)}: {str(e)}")
                self.logger.error(f"Attempted to parse: {json_str[:100]}...")
                self.unprocessed_files.append(os.path.basename(source_file))
                return []
                
        except Exception as e:
            self.logger.error(f"Error during LLM extraction from {os.path.basename(source_file)}: {str(e)}")
            self.unprocessed_files.append(os.path.basename(source_file))
            return []
    
    def _extract_company_name_from_url(self, url: str) -> str:
        """
        Extract a proper company name from a URL.
        
        Args:
            url: The URL to process
            
        Returns:
            Extracted company name
        """
        # Remove common prefixes
        clean_url = url.lower().replace('www.', '').replace('http://', '').replace('https://', '')
        
        # Extract domain without extension
        domain_parts = clean_url.split('.')
        if len(domain_parts) >= 1:
            domain_name = domain_parts[0]
            
            # Handle domains with dashes
            if '-' in domain_name:
                # Convert dashed names to proper casing (e.g., "abc-industries" to "ABC Industries")
                words = [word.capitalize() for word in domain_name.split('-')]
                return ' '.join(words)
            
            # Handle camelCase or single word domains
            if domain_name:
                # Split camelCase if present (e.g., "handyQuilter" to "Handy Quilter")
                result = re.sub(r'([a-z])([A-Z])', r'\1 \2', domain_name)
                # Capitalize properly
                return result.capitalize()
        
        # Fallback if we can't parse it properly
        return url
    
    def _extract_investment_strategy(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract investment strategy, approach, and criteria information from file contents.
        This replaces the separate approach and criteria extraction methods.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Dictionary with extracts and source files
        """
        all_extracts = []
        source_files = set()
        
        # Process all files, looking for investment strategy information
        for file_path, content in file_contents.items():
            # Skip very large files or binary content
            if len(content) > 50000 or not self._is_text_content(content):
                continue
            
            try:
                # Log file being processed
                file_basename = os.path.basename(file_path)
                self.logger.info(f"Extracting investment strategy from: {file_basename}")
                
                # Get the prompt
                prompt = get_investment_strategy_prompt(file_basename, content[:50000], self.current_firm_name)
                
                # Call the LLM
                response = self.llm.invoke(prompt)
                
                # Extract JSON from the response
                extracts = self._extract_json_from_response(response.content)
                
                if extracts and isinstance(extracts, list):
                    for extract in extracts:
                        if isinstance(extract, dict) and "text" in extract:
                            # Add source file information and track unique source files
                            extract["source_file"] = file_basename
                            source_files.add(file_basename)
                            all_extracts.append(extract)
            
            except Exception as e:
                self.logger.error(f"Error extracting investment strategy from {file_basename}: {str(e)}")
        
        self.logger.info(f"Extracted {len(all_extracts)} investment strategy statements from {len(source_files)} files")
        
        # Return both the extracts and the set of source files
        return {
            "extracts": all_extracts,
            "source_files": sorted(list(source_files))
        }

    def _extract_industry_focus(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract industry focus information from file contents.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Dictionary with industry focus extracts and summary
        """
        all_extracts = []
        
        # Process all files, looking for industry focus information
        for file_path, content in file_contents.items():
            # Skip very large files or binary content
            if len(content) > 50000 or not self._is_text_content(content):
                continue
            
            try:
                # Log file being processed
                self.logger.info(f"Extracting industry focus from: {os.path.basename(file_path)}")
                
                # Get the prompt
                prompt = get_industry_focus_prompt(os.path.basename(file_path), content[:50000], self.current_firm_name)
                
                # Call the LLM
                response = self.llm.invoke(prompt)
                
                # Extract JSON from the response
                extracts = self._extract_json_from_response(response.content)
                
                if extracts and isinstance(extracts, list):
                    for extract in extracts:
                        if isinstance(extract, dict) and "text" in extract:
                            # Add source file information
                            extract["source_file"] = os.path.basename(file_path)
                            all_extracts.append(extract)
                
            except Exception as e:
                self.logger.error(f"Error extracting industry focus from {os.path.basename(file_path)}: {str(e)}")
        
        self.logger.info(f"Extracted {len(all_extracts)} industry focus statements")
        
        # Generate a summary of the industry focus
        summary = ""
        if all_extracts:
            try:
                self.logger.info("Generating industry focus summary")
                prompt = get_industry_focus_summary_prompt(all_extracts)
                response = self.llm.invoke(prompt)
                summary = response.content.strip()
            except Exception as e:
                self.logger.error(f"Error generating industry focus summary: {str(e)}")
                summary = "Error generating summary."
        
        return {
            "extracts": all_extracts,
            "summary": summary
        }

    def _extract_geographic_focus(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract geographic focus information from file contents.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Dictionary with geographic focus extracts and summary
        """
        all_extracts = []
        
        # Process all files, looking for geographic focus information
        for file_path, content in file_contents.items():
            # Skip very large files or binary content
            if len(content) > 50000 or not self._is_text_content(content):
                continue
            
            try:
                # Log file being processed
                self.logger.info(f"Extracting geographic focus from: {os.path.basename(file_path)}")
                
                # Get the prompt
                prompt = get_geographic_focus_prompt(os.path.basename(file_path), content[:50000], self.current_firm_name)
                
                # Call the LLM
                response = self.llm.invoke(prompt)
                
                # Extract JSON from the response
                extracts = self._extract_json_from_response(response.content)
                
                if extracts and isinstance(extracts, list):
                    for extract in extracts:
                        if isinstance(extract, dict) and "text" in extract:
                            # Add source file information
                            extract["source_file"] = os.path.basename(file_path)
                            all_extracts.append(extract)
                
            except Exception as e:
                self.logger.error(f"Error extracting geographic focus from {os.path.basename(file_path)}: {str(e)}")
        
        self.logger.info(f"Extracted {len(all_extracts)} geographic focus statements")
        
        # Generate a summary of the geographic focus
        summary = ""
        if all_extracts:
            try:
                self.logger.info("Generating geographic focus summary")
                prompt = get_geographic_focus_summary_prompt(all_extracts)
                response = self.llm.invoke(prompt)
                summary = response.content.strip()
            except Exception as e:
                self.logger.error(f"Error generating geographic focus summary: {str(e)}")
                summary = "Error generating summary."
        
        return {
            "extracts": all_extracts,
            "summary": summary
        }

    def _extract_team_and_contacts(self, file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Extract team and contact information from file contents.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            List of team and contact extracts
        """
        all_extracts = []
        
        # Process all files, looking for team and contact information
        for file_path, content in file_contents.items():
            # Skip very large files or binary content
            if len(content) > 50000 or not self._is_text_content(content):
                continue
            
            try:
                # Log file being processed
                self.logger.info(f"Extracting team and contacts from: {os.path.basename(file_path)}")
                
                # Get the prompt
                prompt = get_team_and_contacts_prompt(os.path.basename(file_path), content[:50000], self.current_firm_name)
                
                # Call the LLM
                response = self.llm.invoke(prompt)
                
                # Extract JSON from the response
                extracts = self._extract_json_from_response(response.content)
                
                if extracts and isinstance(extracts, list):
                    for extract in extracts:
                        if isinstance(extract, dict) and "text" in extract:
                            # Add source file information
                            extract["source_file"] = os.path.basename(file_path)
                            all_extracts.append(extract)
                
            except Exception as e:
                self.logger.error(f"Error extracting team and contacts from {os.path.basename(file_path)}: {str(e)}")
        
        self.logger.info(f"Extracted {len(all_extracts)} team and contact statements")
        return all_extracts

    def _extract_media_and_news(self, file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Extract media and news information from file contents using a two-stage approach:
        1. First check file metadata (filenames) for media indicators
        2. Then perform content-based extraction for other files
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            List of dictionaries containing media and news extracts
        """
        # Log the start of extraction
        self.logger.info("Extracting media and news information")
        
        # Initialize variables
        media_extracts = []
        
        # Stage 1: Keyword-based file matching
        # Keywords that indicate a file likely contains media content
        media_keywords = [
            "news", "media", "press", "insight", "archive", "event", "post", 
            "article", "newsroom", "blog", "case study", "case studies", 
            "acquires", "acquire", "acquisition", "coverage", "release"
        ]
        
        # Files that definitely contain media content based on their names
        media_files = []
        for file_path in file_contents.keys():
            file_basename = os.path.basename(file_path).lower()
            if any(keyword in file_basename for keyword in media_keywords):
                media_files.append(file_path)
                self.logger.info(f"Identified media file by name: {file_basename}")
        
        # Process media files first - include entire content of these files
        for file_path in media_files:
            try:
                content = file_contents[file_path]
                file_basename = os.path.basename(file_path)
                
                # Check if the file is likely to contain text content
                if not self._is_text_content(content):
                    continue
                    
                # Format the content for readability
                formatted_content = self._format_media_content(content)
                
                # Add the entire file as a media item, with sections separated for readability
                media_extracts.append({
                    "text": formatted_content,
                    "location": f"Media file: {file_basename}",
                    "source_file": file_basename
                })
                
                self.logger.info(f"Added entire content of {file_basename} as media item")
                
            except Exception as e:
                self.logger.error(f"Error processing media file {os.path.basename(file_path)}: {str(e)}")
        
        # Stage 2: Content-based extraction for other files
        # Get remaining files that weren't processed in Stage 1
        remaining_files = [path for path in file_contents.keys() if path not in media_files]
        
        # Prioritize files that might have media content based on keywords in content
        priority_files = []
        regular_files = []
        
        for file_path in remaining_files:
            content = file_contents[file_path]
            # Check if content contains media indicators
            if any(term in content.lower() for term in ["announce", "acquisition", "press release", "news"]):
                priority_files.append(file_path)
            else:
                regular_files.append(file_path)
        
        # Process all remaining files, with priority files first
        all_files = priority_files + regular_files
        
        for file_path in all_files:
            try:
                # Check if the file is likely to contain text content
                content = file_contents[file_path]
                if not self._is_text_content(content):
                    continue
                
                file_basename = os.path.basename(file_path)
                is_priority = file_path in priority_files
                
                # Generate the prompt
                prompt = get_media_and_news_prompt(
                    file_basename,
                    content[:40000],  # Limit content to avoid token limits
                    self.current_firm_name,
                    is_priority=is_priority
                )
                
                # Call the LLM
                response = self.llm.invoke(prompt)
                
                # Extract JSON from the response
                extracts = self._extract_json_from_response(response.content)
                
                if extracts and isinstance(extracts, list):
                    # Filter out only blatant placeholder responses
                    valid_extracts = [
                        extract for extract in extracts
                        if isinstance(extract, dict) and "text" in extract and 
                        len(extract["text"]) > 10 and
                        not any(placeholder in extract["text"].lower() for placeholder in ["media", "news", "no media found"])
                    ]
                    
                    if valid_extracts:
                        # Add source_file to each extract
                        for extract in valid_extracts:
                            extract["source_file"] = file_basename
                        
                        self.logger.info(f"Extracted {len(valid_extracts)} media items from {file_basename}")
                        media_extracts.extend(valid_extracts)
                    else:
                        self.logger.info(f"No valid media extracts found in {file_basename}")
                        
                        # For priority files with no extracts, check for patterns directly
                        if is_priority:
                            self.logger.info(f"Attempting pattern-based extraction for {file_basename}")
                            pattern_extracts = self._extract_media_by_patterns(content, file_basename)
                            if pattern_extracts:
                                self.logger.info(f"Found {len(pattern_extracts)} pattern-based extracts in {file_basename}")
                                media_extracts.extend(pattern_extracts)
                else:
                    self.logger.warning(f"Failed to parse media extracts from {file_basename}")
                    
            except Exception as e:
                self.logger.error(f"Error extracting media from {os.path.basename(file_path)}: {str(e)}")
        
        # Log the total number of media extracts
        self.logger.info(f"Total media and news extracts: {len(media_extracts)}")
        return media_extracts

    def _format_media_content(self, content: str) -> str:
        """
        Format media content for better readability.
        
        Args:
            content: Raw content to format
            
        Returns:
            Formatted content string
        """
        # Remove excessive newlines
        formatted = '\n'.join(line for line in content.splitlines() if line.strip())
        
        # Break content into paragraphs for readability
        paragraphs = []
        current_paragraph = []
        
        for line in formatted.splitlines():
            if not line.strip():
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            else:
                current_paragraph.append(line.strip())
        
        # Add the last paragraph if it exists
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        # Join paragraphs with double newlines for readability
        return '\n\n'.join(paragraphs)

    def _extract_media_by_patterns(self, content: str, file_basename: str) -> List[Dict[str, Any]]:
        """
        Extract media content by looking for specific patterns.
        
        Args:
            content: Text content to analyze
            file_basename: Name of the source file
            
        Returns:
            List of extracted media items
        """
        extracts = []
        lines = content.splitlines()
        
        # Define patterns for dates, locations, and news indicators
        date_patterns = [
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b'
        ]
        
        location_patterns = [
            r'[A-Z][A-Z\s]+,\s+[A-Z]{2}',  # NEW YORK, NY
            r'[A-Z][a-z]+,\s+[A-Z]{2}',    # Boston, MA
        ]
        
        news_indicators = [
            "announced today", "has acquired", "completed the sale", 
            "press release", "news release", "acquisition of",
            "announces", "announced", "acquires", "acquired"
        ]
        
        # Process each line looking for patterns
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for patterns in the current line
            has_date = any(re.search(pattern, line) for pattern in date_patterns)
            has_location = any(re.search(pattern, line) for pattern in location_patterns)
            has_indicator = any(indicator in line.lower() for indicator in news_indicators)
            
            # If we found a pattern, extract a full paragraph
            if has_date or has_location or has_indicator:
                # Start with the current line
                paragraph = [line]
                
                # Look back for title (if current line isn't a title)
                if i > 0 and not line.isupper() and not line.endswith(':'):
                    prev_line = lines[i-1].strip()
                    if prev_line and (prev_line.isupper() or (
                        prev_line[0].isupper() and len(prev_line.split()) <= 10)):
                        paragraph.insert(0, prev_line)
                
                # Look ahead for the rest of the paragraph
                j = i + 1
                while j < len(lines) and lines[j].strip():
                    paragraph.append(lines[j].strip())
                    j += 1
                
                # Join the paragraph and add as an extract
                extract_text = ' '.join(paragraph)
                
                # Only add if the paragraph is substantial (more than just a date)
                if len(extract_text) > 20:
                    extracts.append({
                        "text": extract_text,
                        "location": f"Pattern match in {file_basename}",
                        "source_file": file_basename
                    })
                
                # Skip to after this paragraph
                i = j
            else:
                i += 1
        
        return extracts

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
                    return None
            
            # Parse the JSON
            return json.loads(json_str)
        except json.JSONDecodeError:
            self.logger.error(f"JSON parsing error: {response_text[:100]}...")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting JSON: {str(e)}")
            return None

    def _is_text_content(self, content: str) -> bool:
        """
        Check if content is likely text (not binary data).
        
        Args:
            content: Content to check
            
        Returns:
            True if content appears to be text
        """
        # Simple heuristic: check if content is mostly ASCII
        try:
            return len([c for c in content[:1000] if ord(c) < 128]) / len(content[:1000]) > 0.8
        except:
            return False

    def generate_summary_report(self, summary_result: Dict[str, Any]) -> str:
        """
        Generate a well-formatted summary report.
        
        Args:
            summary_result: Dictionary containing all summary information
            
        Returns:
            Formatted report as a string
        """
        if not summary_result["success"]:
            return f"ERROR: {summary_result.get('error', 'Unknown error')}"
        
        directory = summary_result["directory"]
        summary = summary_result["summary"]
        timestamp = summary_result["timestamp"]
        
        # Determine firm name
        firm_name = summary_result.get("firm_name", directory.split('.')[0].capitalize())
        
        # Extract all sections
        portfolio_companies = summary.get("portfolio_companies", [])
        investment_strategy = summary.get("investment_strategy", {"extracts": [], "source_files": []})
        industry_focus = summary.get("industry_focus", {"extracts": [], "summary": ""})
        geographic_focus = summary.get("geographic_focus", {"extracts": [], "summary": ""})
        team_and_contacts = summary.get("team_and_contacts", [])
        media_and_news = summary.get("media_and_news", [])
        
        # Track source files for sections that don't have it built in
        team_sources = sorted(set(extract["source_file"] for extract in team_and_contacts))
        media_sources = sorted(set(extract.get("source_file", "Unknown source") 
                                 for extract in media_and_news 
                                 if isinstance(extract, dict)))
        
        # Count portfolio file companies
        portfolio_file_count = sum(1 for c in portfolio_companies if c.get('from_portfolio_file', False))
        affiliate_count = sum(1 for c in portfolio_companies if c.get('affiliate', False))
        
        # Build the report with semantic sections
        report = f"""
==========================================================================
                DIRECTORY SUMMARY: {directory.upper()}
==========================================================================
Private Equity Firm: {firm_name}
Generated: {timestamp}
Files analyzed: {summary_result['file_count']}
Sections extracted: 6 (Portfolio Companies, Investment Strategy/Criteria, 
                     Industry Focus, Geographic Focus, Team/Contacts, Media/News)
==========================================================================

"""
        
        # INVESTMENT STRATEGY SECTION (combined approach and criteria)
        report += f"""<section name="INVESTMENT_STRATEGY_APPROACH_AND_CRITERIA">
# INVESTMENT STRATEGY, APPROACH & CRITERIA

"""
        if investment_strategy.get("extracts"):
            # Organize extracts by type
            approach_extracts = [e for e in investment_strategy["extracts"] if e.get("type") == "approach"]
            criteria_extracts = [e for e in investment_strategy["extracts"] if e.get("type") == "criteria"]
            other_extracts = [e for e in investment_strategy["extracts"] if e.get("type") not in ["approach", "criteria"]]
            
            # Add approach extracts first
            if approach_extracts:
                report += "## Investment Approach & Philosophy\n\n"
                for extract in approach_extracts:
                    report += f"{extract['text']}\n\n"
            
            # Add criteria extracts next
            if criteria_extracts:
                report += "## Investment Criteria\n\n"
                for extract in criteria_extracts:
                    report += f"{extract['text']}\n\n"
            
            # Add unclassified extracts
            if other_extracts:
                if not (approach_extracts or criteria_extracts):
                    # If no other sections, don't need a header
                    for extract in other_extracts:
                        report += f"{extract['text']}\n\n"
                else:
                    report += "## Additional Investment Information\n\n"
                    for extract in other_extracts:
                        report += f"{extract['text']}\n\n"
        else:
            report += "No specific investment strategy, approach, or criteria information found in the analyzed documents.\n"
        report += "</section>\n\n"
        
        # INDUSTRY FOCUS SECTION
        report += f"""<section name="INDUSTRY_FOCUS">
# INDUSTRY FOCUS

<subsection name="SUMMARY">
"""
        if industry_focus.get("summary"):
            report += f"{industry_focus['summary']}\n"
        else:
            report += "No industry focus summary available.\n"
        report += "</subsection>\n\n"
        
        report += f"""<subsection name="EXTRACTED_CONTENT">
"""
        if industry_focus.get("extracts"):
            for extract in industry_focus["extracts"]:
                report += f"{extract['text']}\n\n"
        else:
            report += "No specific industry focus information found in the analyzed documents.\n"
        report += "</subsection>\n</section>\n\n"
        
        # GEOGRAPHIC FOCUS SECTION
        report += f"""<section name="GEOGRAPHIC_FOCUS">
# GEOGRAPHIC FOCUS

<subsection name="SUMMARY">
"""
        if geographic_focus.get("summary"):
            report += f"{geographic_focus['summary']}\n"
        else:
            report += "No geographic focus summary available.\n"
        report += "</subsection>\n\n"
        
        report += f"""<subsection name="EXTRACTED_CONTENT">
"""
        if geographic_focus.get("extracts"):
            for extract in geographic_focus["extracts"]:
                report += f"{extract['text']}\n\n"
        else:
            report += "No specific geographic focus information found in the analyzed documents.\n"
        report += "</subsection>\n</section>\n\n"
        
        # PORTFOLIO COMPANIES SECTION
        report += f"""<section name="PORTFOLIO_COMPANIES">
# PORTFOLIO COMPANIES

Total portfolio companies: {len(portfolio_companies)}
From portfolio.txt: {portfolio_file_count}
Including affiliate transactions: {affiliate_count}

"""
        
        # First, add all companies from portfolio.txt file
        portfolio_file_companies = [c for c in portfolio_companies if c.get('from_portfolio_file', False)]
        if portfolio_file_companies:
            report += "----- COMPANIES FROM PORTFOLIO.TXT -----\n\n"
            for i, company in enumerate(portfolio_file_companies):
                # Add "(Affiliate)" label for affiliate companies
                company_name = company['name']
                if company.get('affiliate', False):
                    company_name += " (Affiliate)"
                    
                report += f"{i+1}. {company_name}\n"
                
                if company['description'] and company['description'] != "No description available":
                    description = company['description']
                    if "Context:" in description:
                        description = description.replace("Context:", "").strip()
                    report += f"   Description: {description}\n"
                    
                if company['details'] and company['details'] != "No additional details":
                    details = company['details']
                    if "Context:" in details:
                        details = details.replace("Context:", "").strip()
                    report += f"   Details: {details}\n"
                    
                report += "\n"
        
        # Then add companies from other files
        other_companies = [c for c in portfolio_companies if not c.get('from_portfolio_file', False)]
        if other_companies:
            report += "----- COMPANIES FROM OTHER SOURCES -----\n\n"
            for i, company in enumerate(other_companies):
                # Add "(Affiliate)" label for affiliate companies
                company_name = company['name']
                if company.get('affiliate', False):
                    company_name += " (Affiliate)"
                    
                report += f"{i+1}. {company_name}\n"
                
                if company['description'] and company['description'] != "No description available":
                    description = company['description']
                    if "Context:" in description:
                        description = description.replace("Context:", "").strip()
                    report += f"   Description: {description}\n"
                    
                if company['details'] and company['details'] != "No additional details":
                    details = company['details']
                    if "Context:" in details:
                        details = details.replace("Context:", "").strip()
                    report += f"   Details: {details}\n"
                
                report += "\n"
        
        # If no companies were found
        if not portfolio_companies:
            report += "No portfolio companies identified from the analyzed documents.\n"
        report += "</section>\n\n"
        
        # TEAM AND CONTACTS SECTION
        report += f"""<section name="TEAM_AND_CONTACTS">
# TEAM AND CONTACTS

"""
        if team_and_contacts:
            for extract in team_and_contacts:
                report += f"{extract['text']}\n\n"
        else:
            report += "No specific team or contact information found in the analyzed documents.\n"
        report += "</section>\n\n"
        
        # MEDIA AND NEWS SECTION - improved formatting with clear separation between items
        report += f"""<section name="MEDIA_AND_NEWS">
# MEDIA AND NEWS

"""
        
        if media_and_news:
            # Process media items with improved formatting
            for i, extract in enumerate(media_and_news):
                if isinstance(extract, dict) and "text" in extract:
                    text = extract["text"].strip()
                    if text:
                        # Add separator between items for better readability
                        if i > 0:
                            report += f"\n{'-' * 80}\n\n"
                        
                        # Format the text with proper spacing and structure
                        # Split into paragraphs for better readability
                        paragraphs = []
                        lines = text.split("\n")
                        
                        # Process text with improved formatting
                        current_section = []
                        
                        for line in lines:
                            line = line.strip()
                            
                            # Identify section headers (all caps or starts with URL/title indicators)
                            is_header = (line.isupper() or 
                                        line.startswith("URL:") or 
                                        line.startswith("TITLE:") or
                                        (len(line) > 0 and line[0].isupper() and len(line.split()) <= 8))
                            
                            # Format section headers with newlines before them
                            if is_header and current_section:
                                paragraphs.append(" ".join(current_section))
                                current_section = []
                                
                                # Add extra spacing before headers
                                if line.startswith("URL:") or line.startswith("TITLE:"):
                                    paragraphs.append("")  # Add blank line
                                
                                paragraphs.append(line)
                            elif line.startswith("BASE CONTENT:") or "=" * 10 in line:
                                # Special case for base content separators
                                if current_section:
                                    paragraphs.append(" ".join(current_section))
                                    current_section = []
                                paragraphs.append("")  # Add blank line
                                paragraphs.append(line)
                            elif not line:
                                # Empty line indicates paragraph break
                                if current_section:
                                    paragraphs.append(" ".join(current_section))
                                    current_section = []
                                paragraphs.append("")  # Preserve blank line
                            else:
                                # Regular content line - add to current section
                                current_section.append(line)
                        
                        # Add the last paragraph if it exists
                        if current_section:
                            paragraphs.append(" ".join(current_section))
                        
                        # Format financial/fee information in tables or with proper spacing
                        formatted_paragraphs = []
                        for p in paragraphs:
                            # Check if paragraph contains tabular fee data
                            if re.search(r'\$\d+MM\s+\$[\d\.]+MM', p) or re.search(r'\$\d+MM\s+\$[\d,\.]+', p):
                                # Split at dollar signs and format as a table
                                parts = re.split(r'(\$\d+MM\s+\$[\d\.,]+)', p)
                                formatted_parts = []
                                for part in parts:
                                    if re.match(r'\$\d+MM\s+\$[\d\.,]+', part):
                                        # Format fee data with proper spacing
                                        fee_parts = part.split('$')
                                        if len(fee_parts) >= 3:
                                            formatted_parts.append(f"${fee_parts[1].strip()}    ${fee_parts[2].strip()}")
                                    else:
                                        formatted_parts.append(part)
                                formatted_paragraphs.append("".join(formatted_parts))
                            else:
                                formatted_paragraphs.append(p)
                        
                        # Join paragraphs with newlines
                        formatted_text = "\n".join(formatted_paragraphs)
                        
                        # Add the formatted text to the report
                        report += formatted_text
                        report += "\n\n"  # Add extra blank line after each item
        else:
            report += "No media or news information available.\n"
        
        report += "</section>\n\n"
        
        # Add unprocessed files section
        if hasattr(summary_result, 'unprocessed_files') and summary_result.get('unprocessed_files'):
            report += "\n===== FILES WITH PROCESSING ISSUES =====\n\n"
            report += "The following files could not be fully processed by the LLM:\n"
            for file in sorted(set(summary_result['unprocessed_files'])):
                report += f"- {file}\n"
            report += "\nNote: These files were skipped during information extraction.\n"
        
        report += "==========================================================================\n"
        report += "Note: This summary was automatically generated and should be reviewed for accuracy.\n"
        report += "==========================================================================\n"
        
        # Apply token limit before returning
        return self.apply_token_limit(report, max_tokens=65000)

    def _extract_firm_name(self, directory_name: str, file_contents: Dict[str, str]) -> str:
        """
        Extract the private equity firm name from the index.txt file.
        
        Args:
            directory_name: The directory name (domain)
            file_contents: Dictionary of file path to content
            
        Returns:
            Extracted firm name or default name
        """
        # Look for index.txt file
        index_files = [f for f in file_contents.keys() if "index" in f.lower()]
        if not index_files:
            self.logger.warning(f"No index.txt found in {directory_name}, using domain as firm name")
            # Extract domain name from directory (remove .com, etc.)
            domain_parts = directory_name.split('.')
            return domain_parts[0].capitalize()
        
        # Get content from the first index file
        index_content = file_contents[index_files[0]]
        
        # Look for TITLE line in the content
        title_match = re.search(r'TITLE:\s*(.*?)(?:\s*-|\n)', index_content)
        if title_match:
            title = title_match.group(1).strip()
            # Extract first word that seems like a company name
            words = title.split()
            # Skip common words like "Home", "Welcome", etc.
            common_words = ["home", "welcome", "the", "a", "an"]
            for word in words:
                if word.lower() not in common_words and len(word) > 2:
                    self.logger.info(f"Extracted firm name '{word}' from index.txt title")
                    return word
        
        # If we couldn't find a good name in the title, try to find it in the content
        # Look for phrases like "About [Company]", "[Company] is a private equity firm", etc.
        about_match = re.search(r'About\s+(\w+)', index_content)
        if about_match:
            return about_match.group(1)
        
        # If all else fails, use the domain name
        domain_parts = directory_name.split('.')
        firm_name = domain_parts[0].capitalize()
        self.logger.info(f"Using domain as firm name: {firm_name}")
        return firm_name

    def _company_types_compatible(self, name1: str, name2: str) -> bool:
        """
        Check if two companies are of compatible types based on their names.
        
        Args:
            name1: First company name
            name2: Second company name
            
        Returns:
            True if companies appear to be of compatible types
        """
        # Extract company type indicators from names
        def extract_type(name):
            types = []
            name_lower = name.lower()
            
            # Check for specific industry keywords
            if any(term in name_lower for term in ["fluid", "water", "liquid", "pump"]):
                types.append("fluid")
            
            if any(term in name_lower for term in ["display", "retail", "store", "shop"]):
                types.append("retail")
            
            if any(term in name_lower for term in ["handling", "packaging", "container"]):
                types.append("material handling")
            
            if any(term in name_lower for term in ["tech", "software", "digital", "data"]):
                types.append("technology")
            
            return types
        
        type1 = extract_type(name1)
        type2 = extract_type(name2)
        
        # If both have type indicators and they don't overlap, they're different companies
        if type1 and type2 and not set(type1).intersection(set(type2)):
            return False
        
        return True

    def _deduplicate_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate companies by name similarity, preserving content from portfolio file entries.
        
        Args:
            companies: List of company objects
            
        Returns:
            Deduplicated list of company objects
        """
        if not companies:
            return []
        
        # Store original companies for reporting
        self.all_extracted_companies = companies.copy()
        self.duplicate_records = []
        
        # Preprocess to ensure URLs are handled properly
        preprocessed_companies = []
        for company in companies:
            # Check if company name is just a URL/domain
            name = company["name"]
            details = company["details"]
            
            # If the name contains a domain extension but doesn't have website in details
            if (name.lower().endswith('.com') or name.lower().endswith('.net')) and "website:" not in details.lower():
                # Extract proper name and add website to details
                proper_name = self._extract_company_name_from_url(name)
                company["name"] = proper_name
                company["details"] = f"Website: {name}, {details}"
            
            preprocessed_companies.append(company)
        
        # Create separate lists for portfolio and non-portfolio companies
        portfolio_companies = [c for c in preprocessed_companies if c.get('from_portfolio_file', False)]
        other_companies = [c for c in preprocessed_companies if not c.get('from_portfolio_file', False)]
        
        # Create a dictionary to store deduplicated companies
        deduplicated = {}
        
        # First, add all portfolio companies to the deduplicated dictionary
        for company in portfolio_companies:
            name = company["name"]
            normalized_name = name.lower()
            deduplicated[normalized_name] = company
        
        # Log how many portfolio companies were preserved
        self.logger.info(f"Preserved all {len(portfolio_companies)} portfolio file companies")
        
        # Set of normalized portfolio company names for quick lookup
        portfolio_names = set(name.lower() for name in deduplicated.keys())
        
        # Now process non-portfolio companies
        for company in other_companies:
            name = company["name"]
            normalized_name = name.lower()
            
            # Skip if this exact name is already in deduplicated (direct match)
            if normalized_name in deduplicated:
                self.duplicate_records.append({
                    "duplicate_name": name,
                    "matched_with": deduplicated[normalized_name]["name"],
                    "match_type": "exact",
                    "source": company["source_file"]
                })
                
                # Update with additional information if needed
                if company["description"] != "No description available" and deduplicated[normalized_name]["description"] == "No description available":
                    deduplicated[normalized_name]["description"] = company["description"]
                if company["details"] != "No additional details" and deduplicated[normalized_name]["details"] == "No additional details":
                    deduplicated[normalized_name]["details"] = company["details"]
                # Combine source files
                if deduplicated[normalized_name]["source_file"] != company["source_file"]:
                    deduplicated[normalized_name]["source_file"] = f"{deduplicated[normalized_name]['source_file']}, {company['source_file']}"
                continue
            
            # Check for similar companies - using more lenient matching
            found_match = False
            
            for existing_name in list(deduplicated.keys()):
                # Check for domain variants (e.g., "pulsevet" vs "pulsevet.com")
                domain_base = normalized_name.replace('.com', '').replace('.net', '').replace('www.', '')
                existing_base = existing_name.replace('.com', '').replace('.net', '').replace('www.', '')
                
                if domain_base == existing_base:
                    found_match = True
                    self.duplicate_records.append({
                        "duplicate_name": name,
                        "matched_with": deduplicated[existing_name]["name"],
                        "match_type": "domain variant",
                        "source": company["source_file"]
                    })
                    
                    # Update with additional information if available
                    if company["description"] != "No description available" and deduplicated[existing_name]["description"] == "No description available":
                        deduplicated[existing_name]["description"] = company["description"]
                    if company["details"] != "No additional details" and deduplicated[existing_name]["details"] == "No additional details":
                        deduplicated[existing_name]["details"] = company["details"]
                    # Combine source files
                    if deduplicated[existing_name]["source_file"] != company["source_file"]:
                        deduplicated[existing_name]["source_file"] = f"{deduplicated[existing_name]['source_file']}, {company['source_file']}"
                    break
                
                # Use simple name variant matching
                if self._is_same_company_simple(normalized_name, existing_name):
                    found_match = True
                    self.duplicate_records.append({
                        "duplicate_name": name,
                        "matched_with": deduplicated[existing_name]["name"],
                        "match_type": "name variant",
                        "source": company["source_file"]
                    })
                    
                    # Update with additional information if available
                    if company["description"] != "No description available" and deduplicated[existing_name]["description"] == "No description available":
                        deduplicated[existing_name]["description"] = company["description"]
                    if company["details"] != "No additional details" and deduplicated[existing_name]["details"] == "No additional details":
                        deduplicated[existing_name]["details"] = company["details"]
                    # Combine source files
                    if deduplicated[existing_name]["source_file"] != company["source_file"]:
                        deduplicated[existing_name]["source_file"] = f"{deduplicated[existing_name]['source_file']}, {company['source_file']}"
                    break
                
                # Use similarity score as a fallback
                similarity_score = self._name_similarity(normalized_name, existing_name)
                if similarity_score > 0.8:
                    found_match = True
                    self.duplicate_records.append({
                        "duplicate_name": name,
                        "matched_with": deduplicated[existing_name]["name"],
                        "match_type": "similar",
                        "similarity_score": similarity_score,
                        "source": company["source_file"]
                    })
                    
                    # Update with additional information if available
                    if company["description"] != "No description available" and deduplicated[existing_name]["description"] == "No description available":
                        deduplicated[existing_name]["description"] = company["description"]
                    if company["details"] != "No additional details" and deduplicated[existing_name]["details"] == "No additional details":
                        deduplicated[existing_name]["details"] = company["details"]
                    # Combine source files
                    if deduplicated[existing_name]["source_file"] != company["source_file"]:
                        deduplicated[existing_name]["source_file"] = f"{deduplicated[existing_name]['source_file']}, {company['source_file']}"
                    break
            
            # If no match was found, add this as a new company
            if not found_match:
                deduplicated[normalized_name] = company
        
        # Create final deduplicated list
        deduplicated_list = list(deduplicated.values())
        
        # Verify all portfolio companies are included
        portfolio_company_count = sum(1 for company in deduplicated_list if company.get('from_portfolio_file', False))
        self.logger.info(f"Final deduplicated list has {portfolio_company_count} portfolio file companies")
        
        self.logger.info(f"Deduplicated {len(companies)} companies to {len(deduplicated_list)} unique companies")
        
        # Save the kept companies for the report
        self.kept_companies = deduplicated_list.copy()
        
        return deduplicated_list

    def _is_same_company_simple(self, name1: str, name2: str) -> bool:
        """
        Simple check to see if two company names refer to the same entity.
        
        This handles cases like "Company" vs "Company Inc" or "Company" vs "Company Management"
        
        Args:
            name1: First company name (normalized/lowercase)
            name2: Second company name (normalized/lowercase)
            
        Returns:
            True if the names are likely the same company
        """
        # Check if one is a substring of the other at the beginning
        if name1.startswith(name2 + " ") or name2.startswith(name1 + " "):
            return True
        
        # Split into words
        words1 = name1.split()
        words2 = name2.split()
        
        # Skip if lengths are too different
        if len(words1) > 3 and len(words2) > 3 and abs(len(words1) - len(words2)) > 2:
            return False
        
        # Check for common suffixes
        ignore_terms = ["inc", "corp", "llc", "ltd", "management", "solutions", "technologies", "technology", "systems", "products", "group", "company"]
        
        # Get core company name by removing common suffixes
        core_words1 = [w for w in words1 if w.lower() not in ignore_terms]
        core_words2 = [w for w in words2 if w.lower() not in ignore_terms]
        
        # Check if core words are identical
        if len(core_words1) > 0 and len(core_words2) > 0:
            # If one is a single word and it matches the first word of the other, it's a match
            if len(core_words1) == 1 and core_words1[0] == core_words2[0]:
                return True
            if len(core_words2) == 1 and core_words2[0] == core_words1[0]:
                return True
            
            # If all core words match (in any order), it's a match
            if set(core_words1) == set(core_words2):
                return True
        
        return False

    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two company names.
        
        Args:
            name1: First company name
            name2: Second company name
            
        Returns:
            Similarity score (0-1)
        """
        # Normalize names
        name1 = name1.lower()
        name2 = name2.lower()
        
        # Stopwords and common company suffixes to ignore
        ignore_words = ["inc", "corp", "llc", "ltd", "company", "co", "group", 
                       "industries", "solutions", "technology", "technologies",
                       "systems", "products", "services", "management"]
                       
        # Check for location information in parentheses
        location1 = ""
        location2 = ""
        
        # Extract location if present (e.g., "Company Name (Location)")
        loc_match1 = re.search(r'\((.*?)\)', name1)
        loc_match2 = re.search(r'\((.*?)\)', name2)
        
        if loc_match1:
            location1 = loc_match1.group(1).lower()
        if loc_match2:
            location2 = loc_match2.group(1).lower()
        
        # Remove locations from names for comparison
        clean_name1 = re.sub(r'\s*\(.*?\)', '', name1).lower()
        clean_name2 = re.sub(r'\s*\(.*?\)', '', name2).lower()
        
        # Remove common suffixes
        for suffix in ignore_words:
            pattern = r'\b' + re.escape(suffix) + r'\b'
            clean_name1 = re.sub(pattern, '', clean_name1)
            clean_name2 = re.sub(pattern, '', clean_name2)
        
        # Clean up extra spaces
        clean_name1 = re.sub(r'\s+', ' ', clean_name1).strip()
        clean_name2 = re.sub(r'\s+', ' ', clean_name2).strip()
        
        # If one name is completely contained in the other, high similarity
        if clean_name1 in clean_name2 or clean_name2 in clean_name1:
            # If they're exact matches after cleaning
            if clean_name1 == clean_name2:
                return 0.95
            # If one is just a shorter version of the other
            return 0.85
        
        # Split into words for comparison
        words1 = clean_name1.split()
        words2 = clean_name2.split()
        
        # If the first word matches, increase baseline similarity
        baseline = 0.3 if (words1 and words2 and words1[0] == words2[0]) else 0.0
        
        # Count word matches
        common_words = set(words1).intersection(set(words2))
        
        # Calculate Jaccard similarity (intersection over union)
        total_unique_words = len(set(words1).union(set(words2)))
        if total_unique_words == 0:
            return baseline
        
        word_similarity = len(common_words) / total_unique_words
        
        # Boost similarity if first words match
        if words1 and words2 and words1[0] == words2[0]:
            word_similarity = word_similarity * 1.2
        
        # Cap at 1.0
        return min(baseline + word_similarity, 1.0)

    def _save_deduplication_report(self, directory_name: str, output_dir: str) -> Optional[str]:
        """
        Save a report of deduplication decisions.
        
        Args:
            directory_name: The name of the processed directory
            output_dir: Directory to save the report
            
        Returns:
            Path to the saved report or None if no report generated
        """
        if not hasattr(self, 'duplicate_records') or not hasattr(self, 'all_extracted_companies'):
            self.logger.warning("No deduplication data available to generate report")
            return None
        
        try:
            # Generate report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_dir_name = directory_name.replace(".", "_").replace("/", "_")
            filename = f"{safe_dir_name}_deduplication_report_{timestamp}.txt"
            report_path = os.path.join(output_dir, filename)
            
            # Write report
            with open(report_path, "w") as f:
                f.write(f"Deduplication Report for {directory_name}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total companies before deduplication: {len(self.all_extracted_companies)}\n")
                f.write(f"Total companies after deduplication: {len(self.kept_companies)}\n")
                f.write(f"Duplicates found: {len(self.duplicate_records)}\n\n")
                
                # Report on exact matches
                exact_matches = [r for r in self.duplicate_records if r.get('match_type') == 'exact']
                if exact_matches:
                    f.write(f"EXACT MATCHES ({len(exact_matches)}):\n")
                    for match in exact_matches:
                        f.write(f"  \"{match['duplicate_name']}\" -> \"{match['matched_with']}\" [Source: {match['source']}]\n")
                    f.write("\n")
                
                # Report on domain variants
                domain_variants = [r for r in self.duplicate_records if r.get('match_type') == 'domain variant']
                if domain_variants:
                    f.write(f"DOMAIN VARIANTS ({len(domain_variants)}):\n")
                    for match in domain_variants:
                        f.write(f"  \"{match['duplicate_name']}\" -> \"{match['matched_with']}\" [Source: {match['source']}]\n")
                    f.write("\n")
                
                # Report on name variants
                name_variants = [r for r in self.duplicate_records if r.get('match_type') == 'name variant']
                if name_variants:
                    f.write(f"NAME VARIANTS ({len(name_variants)}):\n")
                    for match in name_variants:
                        f.write(f"  \"{match['duplicate_name']}\" -> \"{match['matched_with']}\" [Source: {match['source']}]\n")
                    f.write("\n")
                
                # Report on similarity matches
                similarity_matches = [r for r in self.duplicate_records if r.get('match_type') == 'similar']
                if similarity_matches:
                    f.write(f"SIMILARITY MATCHES ({len(similarity_matches)}):\n")
                    for match in similarity_matches:
                        score = match.get('similarity_score', 'N/A')
                        f.write(f"  \"{match['duplicate_name']}\" -> \"{match['matched_with']}\" (score: {score}) [Source: {match['source']}]\n")
                    f.write("\n")
            
            return report_path
        except Exception as e:
            self.logger.error(f"Error generating deduplication report: {str(e)}")
            return None

    def get_timestamp(self) -> str:
        """Get current timestamp formatted as string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a string using a tokenizer."""
        try:
            tokenizer = AutoTokenizer.from_pretrained("google/gemini-1.5-base")
            tokens = tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            # Fallback approximation if tokenizer fails
            return len(text) // 4  # Rough approximation: ~4 chars per token

    def apply_token_limit(self, report: str, max_tokens: int = 65000) -> str:
        """Apply token limit by preserving as much Media & News content as possible."""
        token_count = self.count_tokens(report)
        
        # If already under limit, return as is
        if token_count <= max_tokens:
            return report
        
        # Find the Media and News section
        media_section_match = re.search(r'(<section name="MEDIA_AND_NEWS">.*?</section>)', report, re.DOTALL)
        
        if not media_section_match:
            # If no media section found, truncate the end as fallback
            self.logger.warning(f"No Media section found for truncation, report is {token_count} tokens")
            return report[:int(len(report) * 0.95)] + "\n\n[Content truncated to meet 65K token limit]"
        
        # Extract the three parts of the report
        before_media = report[:media_section_match.start()]
        media_section = media_section_match.group(1)
        after_media = report[media_section_match.end():]
        
        # Calculate available tokens for the media section
        non_media_tokens = self.count_tokens(before_media + after_media)
        available_media_tokens = max_tokens - non_media_tokens - 100  # Reserve 100 tokens for truncation message
        
        # If we don't have reasonable space for media, replace with minimal notice
        if available_media_tokens < 500:
            truncation_message = "\n<section name=\"MEDIA_AND_NEWS\">\n# MEDIA AND NEWS\n\n[Media content truncated due to token limit]\n</section>"
            return before_media + truncation_message + after_media
        
        # Extract the media section content between section tags
        content_match = re.search(r'<section name="MEDIA_AND_NEWS">(.*?)</section>', media_section, re.DOTALL)
        if not content_match:
            return report  # Something went wrong, return original
        
        media_content = content_match.group(1)
        section_start = "<section name=\"MEDIA_AND_NEWS\">"
        section_end = "</section>"
        
        # Split the media content by horizontal line separators
        # This is a common pattern in the media section from the previous code
        entries = re.split(r'\n{1,2}-{80}\n{1,2}', media_content)
        
        # If no separator found, split by paragraphs
        if len(entries) <= 1:
            entries = re.split(r'\n\n+', media_content)
        
        # Keep the section header
        header_match = re.search(r'(# MEDIA AND NEWS.*?)(?:\n{2,}|\Z)', media_content, re.DOTALL)
        new_media_content = header_match.group(1) if header_match else "# MEDIA AND NEWS\n\n"
        current_tokens = self.count_tokens(section_start + new_media_content + section_end)
        
        # Add entries until we approach the limit
        entries_included = 0
        
        for i, entry in enumerate(entries):
            if not entry.strip() or entry.strip() == "# MEDIA AND NEWS":
                continue
            
            # Add separator before entry (except first non-header entry)
            if entries_included > 0:
                separator = f"\n\n{'-' * 80}\n\n"
                entry_with_separator = separator + entry.strip()
            else:
                entry_with_separator = "\n\n" + entry.strip()
            
            entry_tokens = self.count_tokens(entry_with_separator)
            
            if current_tokens + entry_tokens <= available_media_tokens:
                new_media_content += entry_with_separator
                current_tokens += entry_tokens
                entries_included += 1
            else:
                # No space for this entry
                break
        
        # Add truncation message if we couldn't include all entries
        if entries_included < len([e for e in entries if e.strip() and e.strip() != "# MEDIA AND NEWS"]):
            remaining = len([e for e in entries if e.strip() and e.strip() != "# MEDIA AND NEWS"]) - entries_included
            new_media_content += f"\n\n[{remaining} additional media entries were truncated to meet 65K token limit]"
        
        # Assemble the final report
        truncated_report = before_media + section_start + new_media_content + section_end + after_media
        
        self.logger.info(f"Included {entries_included} media entries while staying under token limit")
        self.logger.info(f"Reduced token count from {token_count} to approximately {self.count_tokens(truncated_report)}")
        
        return truncated_report