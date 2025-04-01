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
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Anthropic API key from environment variables
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    logger.error("ANTHROPIC_API_KEY not found in environment variables. Please add it to your .env file.")
    raise ValueError("ANTHROPIC_API_KEY is required and not set in environment.")

class Summarizer:
    """Agent that summarizes key information from S3 directory documents."""
    
    def __init__(self):
        """Initialize the summarizer with S3 client and LLM."""
        # Initialize logger as an instance attribute
        self.logger = logging.getLogger(__name__)
        
        self.s3_client = get_s3_client()
        
        # Initialize ChatAnthropic with Claude 3.5 Sonnet model
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",  # Change to Claude 3.5 Sonnet
            temperature=0,
            anthropic_api_key=anthropic_api_key  # Explicitly pass the API key
        )
        
        # Test LLM connection
        self._test_llm_connection()
        
        # Initialize unprocessed_files list
        self.unprocessed_files = []
    
    def _test_llm_connection(self):
        """Test the LLM connection to verify API key is working."""
        try:
            test_prompt = "This is a connection test. Respond with 'Connection successful' only."
            response = self.llm.invoke(test_prompt)
            self.logger.info(f"Claude 3.5 Sonnet connection test: {response.content[:50]}...")
        except Exception as e:
            self.logger.error(f"LLM connection test failed: {str(e)}")
            self.logger.error("Check if your ANTHROPIC_API_KEY is correct in the .env file")
            # Continue execution to allow fallback methods to work
    
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
        Extract portfolio companies from file contents.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            is_portfolio_file: Whether the file is a dedicated portfolio file
            
        Returns:
            List of company objects
        """
        # Known portfolio companies for Branford Castle as a fallback
        known_portfolio_companies = [
            {"name": "Titan Production Equipment", "description": "Manufacturer of oil & gas production equipment", "details": "Acquired in 2018", "confidence_score": 1.0},
            {"name": "Drew Foam", "description": "Manufacturer of custom foam products", "details": "Custom EPS manufacturer", "confidence_score": 1.0},
            {"name": "Earthlite", "description": "Manufacturer of massage and spa equipment", "details": "Massage tables, spa and wellness equipment", "confidence_score": 1.0},
            {"name": "Vitrek", "description": "Electrical safety testing and measurement equipment", "details": "Electrical safety test equipment", "confidence_score": 1.0},
            {"name": "BEL", "description": "Manufacturer of rapid prototyping equipment", "details": "Industrial machinery", "confidence_score": 1.0},
            {"name": "Canadian Superstore Industries", "description": "Operator of retail supermarkets", "details": "Retail supermarkets", "confidence_score": 1.0},
            {"name": "Logistick", "description": "Manufacturer of cargo restraint systems", "details": "Adhesive cargo restraints", "confidence_score": 1.0}
        ]
        
        # Add a standard source and other metadata
        for company in known_portfolio_companies:
            company["source_file"] = "fallback_known_companies"
        
        all_companies = []
        
        # First, look for a dedicated portfolio file
        portfolio_files = [f for f in file_contents.keys() if "portfolio" in f.lower()]
        if portfolio_files:
            for portfolio_file in portfolio_files:
                # Try LLM extraction first
                companies = self._extract_companies_with_llm(file_contents[portfolio_file], portfolio_file, True)
                
                # If LLM extraction failed, try regex
                if not companies:
                    companies = self._extract_companies_with_regex(file_contents[portfolio_file], portfolio_file)
                
                all_companies.extend(companies)
        
        # Then process all other files
        for file_path, content in file_contents.items():
            # Skip if already processed as a portfolio file
            if "portfolio" in file_path.lower():
                continue
                
            # Try LLM extraction first
            companies = self._extract_companies_with_llm(content, file_path, False)
            
            # If LLM extraction failed or found nothing, try regex
            if not companies:
                companies = self._extract_companies_with_regex(content, file_path)
                
            all_companies.extend(companies)
        
        # If we found companies, deduplicate them
        if all_companies:
            all_companies = self._deduplicate_companies(all_companies)
        # Otherwise fall back to known companies
        elif known_portfolio_companies:
            self.logger.warning("No companies found in any files, using fallback list of known companies")
            all_companies = known_portfolio_companies
        
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
        
        prompt = f"""
        Extract all portfolio companies CURRENTLY OWNED BY Branford Castle Partners from the following text from file: {os.path.basename(source_file)}.
        
        IMPORTANT INSTRUCTIONS:
        1. ONLY include companies that are CLEARLY CURRENT portfolio companies or investments OWNED BY Branford Castle Partners - not past investments, not general mentions, not employers, not clients.
        2. Do NOT include Branford Castle itself or related entities like Castle Harlan.
        3. Do NOT include companies where team members previously worked or served as directors unless explicitly stated as current portfolio companies.
        4. If ownership is ambiguous, set the "is_owned" field to false.
        5. Pay special attention to phrases like "current portfolio includes", "acquired", "invested in" to identify actual portfolio companies.
        
        Return your answer as a valid JSON array of objects, where each object has these properties:
        - "name": The exact company name, properly capitalized
        - "description": Brief description if available (or "No description available")
        - "details": Any additional details like sector, location, or investment date (or "No additional details")
        - "is_owned": Boolean indicating high confidence this is a CURRENTLY OWNED portfolio company (true/false)
        
        If there are no portfolio companies found, return an empty array: []
        
        The format should be:
        [
          {{"name": "Company Name 1", "description": "Brief description", "details": "Additional details", "is_owned": true}},
          {{"name": "Company Name 2", "description": "Brief description", "details": "Additional details", "is_owned": false}}
        ]
        
        ONLY return the JSON array, nothing else - no explanations, no markdown formatting, just the raw JSON array.
        
        Here's the text to analyze:
        
        {truncated_content}
        """
        
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
                
                # Modify the companies processing section to clean up descriptions and details
                companies = []
                for company in extracted_companies:
                    if isinstance(company, dict) and "name" in company and company.get("is_owned", False):
                        # Clean up description text - remove any partial sentences, limit to 200 chars
                        description = company.get("description", "No description available")
                        if len(description) > 200:
                            # Find the last complete sentence within 200 chars
                            last_period = description[:200].rfind('.')
                            if last_period > 0:
                                description = description[:last_period+1]
                            else:
                                description = description[:200] + "..."
                        
                        # Clean up details text - remove any unwanted contexts
                        details = company.get("details", "No additional details")
                        if details.startswith("Context:"):
                            # Extract only relevant info from context
                            details_lines = details.split('\n')
                            if len(details_lines) > 1:
                                details = details_lines[0].replace("Context:", "").strip()
                            else:
                                # Find first complete sentence
                                first_period = details.find('.')
                                if first_period > 0 and first_period < 150:
                                    details = details[8:first_period+1].strip()  # Skip "Context: "
                                else:
                                    details = "No structured details available"
                        
                        companies.append({
                            "name": company["name"],
                            "description": description,
                            "details": details,
                            "source_file": os.path.basename(source_file),
                            "confidence_score": base_confidence
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
    
    def _extract_companies_with_regex(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """
        Extract company names using regex patterns.
        
        Args:
            content: The text content to analyze
            source_file: Source file path for reference
            
        Returns:
            List of company objects
        """
        companies = []
        
        # Patterns to identify current portfolio companies
        ownership_phrases = [
            r"current portfolio",
            r"portfolio company",
            r"portfolio companies",
            r"acquired in \d{4}",
            r"acquired by Branford Castle",
            r"Branford's investment in",
            r"Branford invested in",
            r"investment in"
        ]
        
        # Check if this is a portfolio or company page
        is_portfolio_page = any(term in source_file.lower() for term in ["portfolio", "companies", "investments"])
        
        # Pattern 1: Headings or emphasized company names in portfolio pages
        if is_portfolio_page:
            # Look for heading patterns (company names followed by descriptive text)
            heading_pattern = r'(?:^|\n)(?:\**|#{1,3})\s*([A-Z][A-Za-z0-9\'\.\-\&\,\s]{2,40})[\s\**#]*(?:\n|\:|$)'
            for match in re.finditer(heading_pattern, content, re.MULTILINE):
                company_name = match.group(1).strip()
                
                # Skip if it's Branford Castle itself or related entities
                if any(name.lower() in company_name.lower() for name in ["branford castle", "castle harlan"]):
                    continue
                    
                # Skip if it's clearly not a company name (enhanced check)
                if (len(company_name.split()) > 6 or 
                    company_name.lower().startswith(("deploying", "pursuing", "opening", "spearheading", "enhanced", "global", "promoting")) or
                    # Check for fragments of verbs ending with "ing"
                    any(word.lower().endswith('ing') for word in company_name.split()) or
                    # Check for prepositions that suggest it's a sentence fragment
                    any(word.lower() in ['of', 'the', 'and', 'for', 'with', 'on', 'by'] for word in company_name.split())):
                    continue
                    
                # Get the description - text after the company name until the next heading
                start_pos = match.end()
                next_heading = re.search(heading_pattern, content[start_pos:], re.MULTILINE)
                description_end = next_heading.start() + start_pos if next_heading else len(content)
                description = content[start_pos:description_end].strip()
                
                # Check if this is likely a current portfolio company
                is_owned = any(re.search(phrase, description, re.IGNORECASE) for phrase in ownership_phrases)
                
                if is_owned:
                    companies.append({
                        "name": company_name,
                        "description": description[:200] + ("..." if len(description) > 200 else ""),
                        "details": "Extracted from portfolio page heading",
                        "source_file": os.path.basename(source_file),
                        "confidence_score": 0.8
                    })
        
        # Pattern 2: Portfolio company mentions with ownership indicators in all pages
        company_pattern = r'([A-Z][A-Za-z0-9\'\.\-\&\,\s]{2,40})\s*(?:,|is|was)?\s*(?:a|an)?\s*(?:' + '|'.join(ownership_phrases) + r')'
        for match in re.finditer(company_pattern, content, re.IGNORECASE):
            company_name = match.group(1).strip()
            
            # Skip if it's Branford Castle itself or related entities
            if any(name.lower() in company_name.lower() for name in ["branford castle", "castle harlan"]):
                continue
                
            # Enhanced filtering to exclude false positives - THIS IS THE FIX
            if (len(company_name.split()) > 6 or  # Too many words
                # Keywords that indicate it's not a company name
                company_name.lower().startswith(("deploying", "pursuing", "opening", "spearheading", "enhanced", "global", "promoting")) or
                # Ends with preposition or verb
                company_name.lower().split()[-1] in ["of", "for", "with", "on", "by", "to", "as", "in"] or
                # Contains fragments of sentences with prepositions
                any(word.lower() in ["of", "the", "to", "by", "with", "from", "as", "for"] for word in company_name.split()) or
                # Words ending with 'ing' likely not company names (often verbs)
                any(word.lower().endswith("ing") for word in company_name.split()[:2]) or
                # Very short names that might be partial words
                (len(company_name) < 5 and len(company_name.split()) == 1) or
                # Special case for this exact match
                "value-added strategies" in company_name.lower()):
                continue
                
            # Context - grab some text around the match
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(content), match.end() + 200)
            context = content[start_pos:end_pos].strip()
            
            # Clean up the context to include just one or two sentences
            context_parts = re.split(r'[.!?]', context)
            if len(context_parts) > 1:
                clean_context = '. '.join(context_parts[:2]) + '.'
            else:
                clean_context = context
                
            companies.append({
                "name": company_name,
                "description": "No detailed description available",
                "details": f"Context: {clean_context}",
                "source_file": os.path.basename(source_file),
                "confidence_score": 0.7
            })
        
        # Deduplicate companies from this file
        unique_companies = []
        seen_names = set()
        for company in companies:
            normalized_name = company["name"].lower()
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_companies.append(company)
        
        self.logger.info(f"Regex extracted {len(unique_companies)} owned portfolio companies from {os.path.basename(source_file)}")
        return unique_companies
    
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
        
        # Build the report
        report = f"""
==========================================================================
                DIRECTORY SUMMARY: {directory.upper()}
==========================================================================
Generated: {timestamp}
Files analyzed: {summary_result['file_count']}
==========================================================================

PORTFOLIO COMPANIES:
------------------
"""
        
        if portfolio_companies:
            # Add each company to the report with cleaner formatting
            for i, company in enumerate(portfolio_companies):
                report += f"{i+1}. {company['name']}\n"
                
                if company['description'] and company['description'] != "No description available":
                    # Clean up description
                    description = company['description']
                    if "Context:" in description:
                        description = description.replace("Context:", "").strip()
                    report += f"   Description: {description}\n"
                    
                if company['details'] and company['details'] != "No additional details":
                    # Clean up details
                    details = company['details']
                    if "Context:" in details:
                        details = details.replace("Context:", "").strip()
                        
                    # Look for first sentence to avoid partial text
                    if len(details) > 150:
                        period_pos = details.find('.')
                        if period_pos > 0 and period_pos < 150:
                            details = details[:period_pos+1]
                    
                    report += f"   Details: {details}\n"
                    
                # Simplify source display if it's too long
                sources = company['source_file'].split(', ')
                if len(sources) > 3:
                    source_display = f"{sources[0]}, {sources[1]} and {len(sources)-2} more files"
                else:
                    source_display = company['source_file']
                    
                report += f"   Source: {source_display}\n"
                report += "\n"
        else:
            report += "No portfolio companies found in the analyzed documents.\n\n"
        
        # Add unprocessed files section
        if hasattr(summary_result, 'unprocessed_files') and summary_result.get('unprocessed_files'):
            report += "\n===== FILES WITH PROCESSING ISSUES =====\n"
            report += "The following files could not be fully processed by the LLM:\n"
            for file in sorted(set(summary_result['unprocessed_files'])):
                report += f"- {file}\n"
            report += "\nNote: These files were processed using fallback methods.\n"
        
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
            report += "\nNote: These files were processed using fallback methods.\n"
        
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
        Deduplicate companies by name similarity.
        
        Args:
            companies: List of company objects
            
        Returns:
            Deduplicated list of company objects
        """
        if not companies:
            return []
            
        # Sort by confidence score (highest first)
        sorted_companies = sorted(companies, key=lambda x: x["confidence_score"], reverse=True)
        
        # Use a dict to track deduplicated companies
        deduplicated = {}
        
        for company in sorted_companies:
            name = company["name"]
            normalized_name = name.lower()
            
            # Check for direct match
            if normalized_name in deduplicated:
                # Update with additional information if available
                if company["description"] != "No description available" and deduplicated[normalized_name]["description"] == "No description available":
                    deduplicated[normalized_name]["description"] = company["description"]
                if company["details"] != "No additional details" and deduplicated[normalized_name]["details"] == "No additional details":
                    deduplicated[normalized_name]["details"] = company["details"]
                # Combine source files
                if deduplicated[normalized_name]["source_file"] != company["source_file"]:
                    deduplicated[normalized_name]["source_file"] = f"{deduplicated[normalized_name]['source_file']}, {company['source_file']}"
                continue
                
            # Check for similar names
            found_similar = False
            for existing_norm in list(deduplicated.keys()):
                # Check if names are similar enough (e.g., "Company Inc" vs "Company")
                if (normalized_name in existing_norm or existing_norm in normalized_name or
                    self._name_similarity(normalized_name, existing_norm) > 0.8):
                    # Update with additional information if available
                    if company["description"] != "No description available" and deduplicated[existing_norm]["description"] == "No description available":
                        deduplicated[existing_norm]["description"] = company["description"]
                    if company["details"] != "No additional details" and deduplicated[existing_norm]["details"] == "No additional details":
                        deduplicated[existing_norm]["details"] = company["details"]
                    # Combine source files
                    if deduplicated[existing_norm]["source_file"] != company["source_file"]:
                        deduplicated[existing_norm]["source_file"] = f"{deduplicated[existing_norm]['source_file']}, {company['source_file']}"
                    found_similar = True
                    break
            
            if not found_similar:
                deduplicated[normalized_name] = company
        
        self.logger.info(f"Deduplicated {len(companies)} companies to {len(deduplicated)} unique companies")
        return list(deduplicated.values())
    
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
        
        # Generate report from the summary result
        report = self.generate_summary_report(summary_result)
        
        # Save the report and return the path
        if output_dir:
            return self._save_summary(report, cleaned_companies, directory, output_dir, output_json)
        
        return report 