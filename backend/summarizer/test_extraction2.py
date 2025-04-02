import os
import sys
import logging
from pathlib import Path
import re
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Import the necessary components
from backend.aws.s3 import get_s3_client
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Output directory
OUTPUT_DIR = current_dir / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_portfolio_companies():
    """
    Extract portfolio companies from portfolio.txt using a simple, direct prompt.
    Saves results as a text file in the output directory.
    """
    # Get Google API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY not found in environment variables")
        return None
    
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-exp-03-25",
        temperature=0,
        google_api_key=google_api_key
    )
    
    # Get the portfolio.txt file from S3
    s3_client = get_s3_client()
    dir_name = "branfordcastle.com"
    
    # Get all files and find portfolio.txt
    try:
        files = s3_client.list_files_by_directory().get(dir_name, [])
        portfolio_file = next((f for f in files if "portfolio" in f.lower()), None)
        
        if not portfolio_file:
            logger.error("No portfolio file found")
            return None
        
        logger.info(f"Found portfolio file: {portfolio_file}")
        content = s3_client.get_file_content(portfolio_file)
        
        if not content:
            logger.error(f"Failed to get content for file: {portfolio_file}")
            return None
        
        # Simple, direct prompt format with clear JSON instructions
        prompt = f"""
        Please extract all portfolio companies owned by Branford Castle from the following text.
        
        IMPORTANT INSTRUCTIONS:
        1. ONLY include companies where a specific company name OR website domain is provided
        2. DO NOT include any companies described only by their function
        3. For each company, extract: name, description, and website/details
        
        Return your response as a JSON array using this format exactly:
        [
          {{
            "name": "Company Name",
            "description": "Brief description of what they do",
            "details": "Website or additional information"
          }}
        ]
        
        Only return the JSON array, nothing else.
        
        Here's the text to analyze:
        
        {content}
        """
        
        # Call the LLM with the prompt
        logger.info("Calling LLM to extract portfolio companies...")
        response = llm.invoke(prompt)
        response_text = response.content
        
        # Extract the JSON content if it exists
        json_match = re.search(r'(\[\s*\{.*\}\s*\])', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                companies = json.loads(json_str)
                
                # Format the companies in a clean way similar to the example
                formatted_companies = ""
                for i, company in enumerate(companies):
                    formatted_companies += f"{i+1}. {company.get('name', 'Unknown')}\n"
                    formatted_companies += f"   Description: {company.get('description', 'No description available')}\n"
                    formatted_companies += f"   Details: {company.get('details', 'No additional details')}\n\n"
                
                # Generate test report with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_filename = f"clean_portfolio_extraction_{timestamp}.txt"
                report_path = OUTPUT_DIR / report_filename
                
                # Create the report
                report = f"""
==========================================================================
                PORTFOLIO COMPANIES EXTRACTION (NAMED ONLY)
==========================================================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
File analyzed: {portfolio_file}
==========================================================================

EXTRACTED COMPANIES:
==========================================================================

{formatted_companies}==========================================================================
"""
                
                # Make sure output directory exists
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                
                # Save the report
                try:
                    with open(report_path, "w") as f:
                        f.write(report)
                    logger.info(f"Extraction results saved to: {report_path}")
                except Exception as e:
                    logger.error(f"Error saving report to {report_path}: {str(e)}")
                    return None
                
                logger.info(f"Extracted {len(companies)} named portfolio companies")
                
                return {
                    "company_count": len(companies),
                    "report_path": report_path,
                    "response_text": formatted_companies
                }
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
        
        # If we got here, JSON parsing failed
        logger.error("Failed to extract valid company data from LLM response")
        logger.error(f"Raw response start: {response_text[:200]}...")
        return None
        
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    """Main entry point for the simple portfolio extraction test."""
    logger.info("Starting simple portfolio company extraction test")
    
    # Run the extraction
    result = extract_portfolio_companies()
    
    if result:
        logger.info(f"Successfully extracted approximately {result['company_count']} companies")
        logger.info(f"Results saved to: {result['report_path']}")
        
        # Display first few lines of the response
        lines = result['response_text'].split('\n')
        preview_lines = lines[:min(10, len(lines))]
        logger.info("Preview of extraction results:")
        for line in preview_lines:
            if line.strip():
                logger.info(line)
        if len(lines) > 10:
            logger.info("... (more results in the output file)")
    else:
        logger.warning("Extraction failed")
    
    logger.info("Portfolio extraction test completed")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 