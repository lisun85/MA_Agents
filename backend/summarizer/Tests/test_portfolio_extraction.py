import os
import sys
import json
import logging
from pathlib import Path
import re
from datetime import datetime

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

# Custom prompts for testing
def get_test_prompt(source_file: str, content: str, variation: int = 0) -> str:
    """
    Generate a simple, direct prompt asking for portfolio companies.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        
    Returns:
        Formatted prompt string
    """
    # Simple, direct question prompt
    prompt = f"""
    Please provide all portfolio companies owned by Branford Castle from the following text.
    
    Return your answer as a JSON array with the following structure:
    [
      {{"name": "Company Name", "description": "Brief description", "details": "Additional details", "is_owned": true}}
    ]
    
    Make sure to include all companies mentioned in the text.
    
    ONLY return the JSON array.
    """
    
    # Add the content at the end
    prompt += f"\n\nHere's the text from {source_file}:\n\n{content}"
    
    return prompt

def extract_json_from_response(response_text):
    """Extract JSON array from LLM response text."""
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
            logger.error("Failed to extract JSON from LLM response")
            return []
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        logger.error(f"Attempted to parse: {json_str[:100]}...")
        return []

def test_extraction():
    """Test extraction from portfolio.txt using a simple prompt."""
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
        
        # Define our simple prompt for text output
        prompt = f"""
        Please provide all portfolio companies owned by Branford Castle from the following text.
        
        For each company, include:
        1. The company name
        2. A brief description of what the company does
        3. Any additional details like industry, acquisition date, etc.
        
        Format your response as a numbered list with these details for each company.
        
        Here's the text from {os.path.basename(portfolio_file)}:
        
        {content}
        """
        
        # Call the LLM with the prompt
        logger.info(f"Calling LLM...")
        response = llm.invoke(prompt)
        response_text = response.content
        
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Generate test report with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"portfolio_companies_{timestamp}.txt"
        report_path = OUTPUT_DIR / report_filename
        
        # Create the report (without showing the prompt)
        report = f"""
==========================================================================
                PORTFOLIO EXTRACTION RESULTS
==========================================================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
File analyzed: {portfolio_file}
==========================================================================

EXTRACTED COMPANIES:
==========================================================================

{response_text}
==========================================================================
"""
        
        # Make sure output directory exists
        if not os.path.exists(OUTPUT_DIR):
            logger.info(f"Creating output directory: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Save the report
        try:
            with open(report_path, "w") as f:
                f.write(report)
            logger.info(f"Test report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Error saving report to {report_path}: {str(e)}")
        
        # Extract company names from the response text (approximate)
        company_names = []
        for line in response_text.split('\n'):
            # Look for numbered lines that likely contain company names
            if re.match(r'^\d+\.?\s+', line):
                # Extract just the company name (assuming it's at the start after the number)
                name_match = re.search(r'^\d+\.?\s+(.*?)(?:\s*[-:–]|$)', line)
                if name_match:
                    company_name = name_match.group(1).strip()
                    if company_name:
                        company_names.append(company_name)
        
        logger.info(f"Extracted approximately {len(company_names)} companies")
        
        return {
            "company_count": len(company_names),
            "report_path": report_path,
            "company_names": company_names
        }
        
    except Exception as e:
        logger.error(f"Error during extraction test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    """Main entry point for the portfolio extraction test tool."""
    logger.info("Starting portfolio extraction test")
    
    # Make sure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        logger.info(f"Creating output directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run the extraction test
    result = test_extraction()
    
    if result:
        logger.info(f"Successfully extracted approximately {result['company_count']} companies")
        logger.info(f"Test report saved to: {result['report_path']}")
        
        # Print company names
        for i, name in enumerate(result['company_names']):
            logger.info(f"{i+1}. {name}")
    else:
        logger.warning("No results from extraction test")
    
    logger.info("Portfolio extraction test completed")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 