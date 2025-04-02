import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
import json
from datetime import datetime
import re

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
from backend.summarizer.prompts import get_company_extraction_prompt, get_connection_test_prompt

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
        
        # Initialize Google Gemini 2.5 Pro Experimental model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro-exp-03-25",  # Specific Gemini 2.5 Pro experimental model
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
            self.logger.info(f"Google Gemini 2.5 Pro connection test: {response.content[:50]}...")
        except Exception as e:
            self.logger.error(f"LLM connection test failed: {str(e)}")
            self.logger.error("Check if your GOOGLE_API_KEY is correct in the .env file")
            # Continue execution to allow the program to run
    
    def summarize_directory(self, directory_name: str) -> Dict[str, Any]:
        """
        Extract and summarize key information from a directory in S3.
        
        Args:
            directory_name: The name of the directory in S3 (e.g., "branfordcastle.com")
            
        Returns:
            Dict containing summary data and metadata
        """
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
        
        # Step 4: Extract portfolio companies
        self.logger.info("Extracting portfolio companies...")
        portfolio_companies = self._extract_portfolio_companies(file_content_map)
        
        # Step 5: Create the summary result
        summary_result = {
            "success": True,
            "directory": directory_name,
            "file_count": len(contents),
            "summary": {
                "portfolio_companies": portfolio_companies
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.logger.info(f"Summarization complete. Found {len(portfolio_companies)} portfolio companies.")
        return summary_result
    
    def _extract_portfolio_companies(self, file_contents, is_portfolio_file=False):
        """
        Extract portfolio companies from file contents using LLM only.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            is_portfolio_file: Whether the file is a dedicated portfolio file
            
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
                companies = self._extract_companies_with_llm(file_contents[portfolio_file], portfolio_file, True)
                
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
            companies = self._extract_companies_with_llm(content, file_path, False)
            
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
    
    def _extract_companies_with_llm(self, content: str, source_file: str, is_portfolio_file: bool) -> List[Dict[str, Any]]:
        """
        Use LLM to extract company names from content.
        
        Args:
            content: The text content to analyze
            source_file: Source file path for reference
            is_portfolio_file: Whether this is a dedicated portfolio file
            
        Returns:
            List of company objects
        """
        # Set confidence score based on file type
        base_confidence = 0.9 if is_portfolio_file else 0.7
        
        # Truncate content to avoid token limits
        truncated_content = content[:50000]
        
        # Get the prompt from the prompts module
        prompt = get_company_extraction_prompt(os.path.basename(source_file), truncated_content)
        
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
    
    def generate_summary_report(self, summary_result: Dict[str, Any]) -> str:
        """
        Generate a formatted summary report.
        
        Args:
            summary_result: The result from summarize_directory
            
        Returns:
            Formatted report as a string
        """
        if not summary_result["success"]:
            return f"ERROR: {summary_result.get('error', 'Unknown error')}"
        
        directory = summary_result["directory"]
        summary = summary_result["summary"]
        portfolio_companies = summary.get("portfolio_companies", [])
        timestamp = summary_result["timestamp"]
        
        # Count portfolio file companies
        portfolio_file_count = sum(1 for c in portfolio_companies if c.get('from_portfolio_file', False))
        affiliate_count = sum(1 for c in portfolio_companies if c.get('affiliate', False))
        
        # Build the report
        report = f"""
==========================================================================
                DIRECTORY SUMMARY: {directory.upper()}
==========================================================================
Generated: {timestamp}
Files analyzed: {summary_result['file_count']}
Portfolio.txt companies: {portfolio_file_count}
Including affiliate transactions: {affiliate_count}
Total portfolio companies: {len(portfolio_companies)}
==========================================================================

PORTFOLIO COMPANIES:
------------------
"""
        
        # First, add all companies from portfolio.txt file
        portfolio_file_companies = [c for c in portfolio_companies if c.get('from_portfolio_file', False)]
        if portfolio_file_companies:
            report += "\n----- COMPANIES FROM PORTFOLIO.TXT -----\n\n"
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
                    
                # Simplify source display
                sources = company['source_file'].split(', ')
                if len(sources) > 3:
                    source_display = f"{sources[0]}, {sources[1]} and {len(sources)-2} more files"
                else:
                    source_display = company['source_file']
                    
                report += f"   Source: {source_display}\n\n"
        
        # Then add companies from other files
        other_companies = [c for c in portfolio_companies if not c.get('from_portfolio_file', False)]
        if other_companies:
            report += "\n----- COMPANIES FROM OTHER SOURCES -----\n\n"
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
                    
                # Simplify source display
                sources = company['source_file'].split(', ')
                if len(sources) > 3:
                    source_display = f"{sources[0]}, {sources[1]} and {len(sources)-2} more files"
                else:
                    source_display = company['source_file']
                    
                report += f"   Source: {source_display}\n\n"
        
        # If no companies were found
        if not portfolio_companies:
            report += "No portfolio companies identified from the analyzed documents.\n"
            report += "This could indicate either:\n"
            report += "1. The documents don't contain portfolio company information\n"
            report += "2. The LLM extraction method couldn't identify portfolio companies\n\n"
        
        # Add unprocessed files section
        if hasattr(summary_result, 'unprocessed_files') and summary_result.get('unprocessed_files'):
            report += "\n===== FILES WITH PROCESSING ISSUES =====\n"
            report += "The following files could not be fully processed by the LLM:\n"
            for file in sorted(set(summary_result['unprocessed_files'])):
                report += f"- {file}\n"
            report += "\nNote: These files were skipped during portfolio company extraction.\n"
        
        report += "==========================================================================\n"
        report += "Note: This summary was automatically generated and should be reviewed for accuracy.\n"
        report += "==========================================================================\n"
        
        return report

    def _generate_summary_report(self, companies: List[Dict[str, Any]], directory_name: str) -> str:
        """
        Generate a summary report for the directory.
        
        Args:
            companies: List of company objects
            directory_name: Name of the directory
            
        Returns:
            Summary report text
        """
        # ... existing code ...
        
        # Add summary of companies found
        report += f"\nAnalysis found {len(companies)} portfolio companies currently owned by Branford Castle Partners:\n\n"
        
        # Add each company to the report
        for i, company in enumerate(companies, 1):
            report += f"{i}. {company['name']}\n"
            report += f"   Description: {company['description']}\n"
            report += f"   Details: {company['details']}\n"
            report += f"   Source: {company['source_file']}\n"
            report += f"   Confidence: {company['confidence_score']}\n\n"
        
        # Add unprocessed files section
        if hasattr(self, 'unprocessed_files') and self.unprocessed_files:
            report += "\n===== FILES WITH PROCESSING ISSUES =====\n"
            report += "The following files could not be fully processed by the LLM:\n"
            for file in sorted(set(self.unprocessed_files)):
                report += f"- {file}\n"
            report += "\nNote: These files were skipped during portfolio company extraction.\n"
        
        return report

    def _save_summary(self, report: str, companies: List[Dict[str, Any]], directory_name: str, output_dir: str, output_json: bool) -> str:
        """
        Save summary report to file.
        
        Args:
            report: Summary report text
            companies: List of company objects
            directory_name: Name of the directory
            output_dir: Directory to save output
            output_json: Whether to output JSON
            
        Returns:
            Path to summary report
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize directory name for filename
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in directory_name)
        safe_name = safe_name.replace(" ", "_").lower()
        
        # Generate report filename
        report_filename = f"{safe_name}_analysis_report.txt"
        report_path = os.path.join(output_dir, report_filename)
        
        # Write report to file
        with open(report_path, "w") as f:
            f.write(report)
        
        self.logger.info(f"Saved summary report to {report_path}")
        
        # Save JSON if requested
        if output_json:
            json_filename = f"{safe_name}_analysis_data.json"
            json_path = os.path.join(output_dir, json_filename)
            
            # Prepare JSON data
            json_data = {
                "directory": directory_name,
                "portfolio_companies": companies,
                "company_count": len(companies)
            }
            
            # Add unprocessed files to JSON data
            if hasattr(self, 'unprocessed_files') and self.unprocessed_files:
                json_data["unprocessed_files"] = sorted(set(self.unprocessed_files))
            
            # Write JSON to file
            with open(json_path, "w") as f:
                json.dump(json_data, f, indent=2)
            
            self.logger.info(f"Saved JSON data to {json_path}")
        
        return report_path

    def _deduplicate_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate companies by name similarity, preserving ALL portfolio file entries.
        
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
            if (name.lower().endswith('.com') or name.lower().endswith('.net')) and "website" not in details.lower():
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
        
        # First, add ALL portfolio companies to the deduplicated list
        # This ensures we don't lose ANY entries from portfolio.txt
        for company in portfolio_companies:
            name = company["name"]
            normalized_name = name.lower()
            deduplicated[normalized_name] = company
        
        # Log how many portfolio companies were preserved
        self.logger.info(f"Preserved all {len(portfolio_companies)} portfolio file companies")
        
        # Now process non-portfolio companies, only merging them if they're obvious duplicates
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
            
            # Check for similar companies, but ONLY for non-portfolio companies
            # This avoids merging different portfolio companies together
            found_match = False
            for existing_name in list(deduplicated.keys()):
                # Skip if the existing company is from portfolio.txt
                if deduplicated[existing_name].get('from_portfolio_file', False):
                    # Only consider an exact match or domain variant for portfolio companies
                    if normalized_name == existing_name:
                        found_match = True
                        break
                    
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
                
                continue
            
            # For non-portfolio companies, use standard similarity check
            similarity_score = self._name_similarity(normalized_name, existing_name)
            if similarity_score > 0.85:  # Stricter threshold
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
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two company names.
        
        Args:
            name1: First company name
            name2: Second company name
            
        Returns:
            Similarity score (0-1)
        """
        # Remove common suffixes for comparison
        suffixes = [" inc", " corp", " llc", " ltd", " co", " company", " group", " holdings"]
        clean_name1 = name1
        clean_name2 = name2
        
        for suffix in suffixes:
            clean_name1 = clean_name1.replace(suffix, "")
            clean_name2 = clean_name2.replace(suffix, "")
        
        # Compute Levenshtein distance
        distance = 0
        m, n = len(clean_name1), len(clean_name2)
        
        # Simple case: if one is empty, distance is length of the other
        if m == 0:
            return 0
        if n == 0:
            return 0
            
        # Early exit for exact match
        if clean_name1 == clean_name2:
            return 1.0
            
        # Use a simple ratio of matching characters
        matches = 0
        for c1 in clean_name1:
            if c1 in clean_name2:
                matches += 1
                
        return matches / max(m, n)

    def _clean_company_data(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean up company data to remove partial sentences and irrelevant context.
        
        Args:
            companies: List of company objects
            
        Returns:
            Cleaned list of company objects
        """
        cleaned_companies = []
        
        for company in companies:
            # Clean up description
            description = company.get("description", "")
            if "Context:" in description:
                description = description.replace("Context:", "").strip()
                # Find first complete sentence
                first_period = description.find('.')
                if first_period > 0:
                    description = description[:first_period+1]
                
            # Clean up details
            details = company.get("details", "")
            if "Context:" in details:
                details = details.replace("Context:", "").strip()
                # Find the first sentence if it's long
                if len(details) > 100:
                    first_period = details.find('.')
                    if first_period > 0 and first_period < 100:
                        details = details[:first_period+1]
            
            # Create cleaned company entry
            cleaned_company = company.copy()
            cleaned_company["description"] = description if description else "No description available"
            cleaned_company["details"] = details if details else "No additional details"
            
            cleaned_companies.append(cleaned_company)
        
        return cleaned_companies

    def summarize(self, directory: str, output_dir: str = None, output_json: bool = False) -> str:
        """
        Summarize the directory contents and save the report.
        
        Args:
            directory: Directory name to analyze
            output_dir: Directory to save output files
            output_json: Whether to save JSON data
            
        Returns:
            Path to the summary report file
        """
        # Reset unprocessed files list
        self.unprocessed_files = []
        
        # Get the summary result
        summary_result = self.summarize_directory(directory)
        
        if not summary_result["success"]:
            self.logger.error(f"Summarization failed: {summary_result.get('error', 'Unknown error')}")
            return None
        
        # Clean up company data
        companies = summary_result["summary"]["portfolio_companies"]
        cleaned_companies = self._clean_company_data(companies)
        summary_result["summary"]["portfolio_companies"] = cleaned_companies
        
        # Generate and save the deduplication report if we have the data
        if hasattr(self, 'all_extracted_companies') and output_dir:
            try:
                dedup_path = self._save_deduplication_report(directory, output_dir)
                self.logger.info(f"Generated deduplication report at: {dedup_path}")
            except Exception as e:
                self.logger.error(f"Error generating deduplication report: {str(e)}")
        else:
            self.logger.warning("No deduplication data available for reporting")
        
        # Generate report from the summary result
        report = self.generate_summary_report(summary_result)
        
        # Save the report and return the path
        if output_dir:
            return self._save_summary(report, cleaned_companies, directory, output_dir, output_json)
        
        return report

    def _save_deduplication_report(self, directory_name: str, output_dir: str) -> str:
        """
        Save a detailed report of the deduplication process.
        
        Args:
            directory_name: The name of the directory
            output_dir: Directory to save output
            
        Returns:
            Path to the deduplication report file
        """
        if not hasattr(self, 'all_extracted_companies') or not hasattr(self, 'duplicate_records'):
            self.logger.warning("No deduplication data available")
            return None
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize directory name for filename
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in directory_name)
        safe_name = safe_name.replace(" ", "_").lower()
        
        # Generate report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{safe_name}_deduplication_report_{timestamp}.txt"
        report_path = os.path.join(output_dir, report_filename)
        
        # Count affiliates
        affiliate_count = sum(1 for c in self.all_extracted_companies if c.get('affiliate', False))
        final_affiliate_count = sum(1 for c in self.kept_companies if c.get('affiliate', False))
        
        # Build the report
        report = f"""
==========================================================================
            DEDUPLICATION REPORT: {directory_name.upper()}
==========================================================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
==========================================================================

SUMMARY:
-------
Total companies extracted: {len(self.all_extracted_companies)}
Including affiliate transactions: {affiliate_count}
Duplicates found: {len(self.duplicate_records)}
Final unique companies: {len(self.kept_companies)}
Final affiliate transactions: {final_affiliate_count}

==========================================================================
ALL EXTRACTED COMPANIES ({len(self.all_extracted_companies)}):
==========================================================================
"""
        
        # Add each extracted company
        for i, company in enumerate(self.all_extracted_companies):
            # Add "(Affiliate)" label if needed
            company_name = company['name']
            if company.get('affiliate', False):
                company_name += " (Affiliate)"
                
            report += f"{i+1}. {company_name}\n"
            report += f"   Description: {company['description']}\n"
            report += f"   Source: {company['source_file']}\n"
            report += f"   Confidence Score: {company['confidence_score']}\n\n"
        
        report += f"""
==========================================================================
DUPLICATE COMPANIES ({len(self.duplicate_records)}):
==========================================================================
"""
        
        # Add each duplicate and what it matched with
        for i, dup in enumerate(self.duplicate_records):
            report += f"{i+1}. \"{dup['duplicate_name']}\" was merged with \"{dup['matched_with']}\"\n"
            report += f"   Match Type: {dup['match_type']}\n"
            if 'similarity_score' in dup:
                report += f"   Similarity Score: {dup['similarity_score']:.2f}\n"
            report += f"   Source: {dup['source']}\n\n"
        
        report += f"""
==========================================================================
FINAL UNIQUE COMPANIES ({len(self.kept_companies)}):
==========================================================================
"""
        
        # Add each final company
        for i, company in enumerate(self.kept_companies):
            # Add "(Affiliate)" label if needed
            company_name = company['name']
            if company.get('affiliate', False):
                company_name += " (Affiliate)"
                
            report += f"{i+1}. {company_name}\n"
            report += f"   Description: {company['description']}\n"
            report += f"   Details: {company['details']}\n"
            report += f"   Source: {company['source_file']}\n"
            report += f"   Confidence Score: {company['confidence_score']}\n\n"
        
        report += "==========================================================================\n"
        
        # Write report to file
        with open(report_path, "w") as f:
            f.write(report)
        
        self.logger.info(f"Deduplication report saved to: {report_path}")
        
        return report_path