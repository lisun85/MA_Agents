import os
import sys
import logging
import json
from pathlib import Path
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from backend.reasoning_agent.prompts import PROMPT
from backend.reasoning_agent.config import (
    MODEL_ID, TEMPERATURE, OUTPUT_DIR, 
    S3_BUCKET, S3_REGION, S3_SUMMARIES_PREFIX,
    MAX_COMPANIES_TO_PROCESS, SKIP_EXISTING_OUTPUTS
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('reasoning_agent.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure the output directory exists
output_dir = Path(OUTPUT_DIR)
output_dir.mkdir(parents=True, exist_ok=True)

def get_s3_client():
    """
    Create and return an S3 client using environment variables or default settings.
    """
    try:
        # Configure S3 client
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', S3_REGION)
        )
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        raise

def list_company_files():
    """
    List all company summary files in the S3 bucket.
    """
    try:
        s3_client = get_s3_client()
        
        # List objects with the summaries prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_SUMMARIES_PREFIX
        )
        
        # Check if there are any files
        if 'Contents' not in response:
            logger.warning(f"No company files found in {S3_BUCKET}/{S3_SUMMARIES_PREFIX}")
            return []
        
        # Process each file to extract company name
        company_files = []
        for obj in response['Contents']:
            file_key = obj['Key']
            # Skip any non-txt files or directories
            if not file_key.endswith('.txt'):
                continue
                
            # Extract filename from the key
            filename = os.path.basename(file_key)
            
            # Extract company name (all characters before first underscore)
            company_name = extract_company_name(filename)
            
            company_files.append({
                'key': file_key,
                'filename': filename,
                'company_name': company_name,
                'size': obj['Size']
            })
        
        logger.info(f"Found {len(company_files)} company files in S3")
        return company_files
        
    except Exception as e:
        logger.error(f"Error listing company files: {str(e)}")
        return []

def extract_company_name(filename):
    """
    Extract company name from filename (characters before first underscore).
    """
    # Split by underscore and take the first part
    parts = filename.split('_')
    if parts:
        return parts[0]
    return "unknown"  # Fallback if no underscore found

def check_output_exists(company_name):
    """
    Check if an output file already exists for this company.

    """
    if not SKIP_EXISTING_OUTPUTS:
        return False
        
    # Check if any files in the output directory start with the company name
    for file in output_dir.glob(f"{company_name}_*.txt"):
        return True
    return False

def retrieve_company_info(file_key):
    """
    Retrieve a specific company summary from S3.
    """
    s3_client = get_s3_client()
    
    try:
        logger.info(f"Retrieving company info from S3: {file_key}")
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=file_key)
        content = response['Body'].read().decode('utf-8')
        logger.info(f"Successfully retrieved {len(content)} characters of company data")
        return content
    except Exception as e:
        logger.error(f"Error retrieving file from S3: {str(e)}")
        raise Exception(f"Failed to retrieve {file_key} from S3: {str(e)}")

class DeepSeekReasoner:
    """
    A wrapper class for the DeepSeek Reasoning API.
    """
    def __init__(self, model_id, temperature=0):
        self.model_id = model_id
        self.temperature = temperature
        # Get API key from environment variables only
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key not found in .env file. Please add DEEPSEEK_API_KEY to your .env file.")
        logger.info(f"Initialized DeepSeekReasoner with model: {model_id}")
        
    def generate(self, prompt):
        """
        Generate a response using the DeepSeek Reasoning API.
        Captures both reasoning_content (Chain of Thought) and the final content.
        """
        try:
            from openai import OpenAI
            
            # Initialize client with DeepSeek API base URL
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            
            # Create the completion request
            response = client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            
            # Extract both reasoning content and final response
            reasoning_content = response.choices[0].message.reasoning_content
            final_content = response.choices[0].message.content
            
            # Create a combined output with cleaner formatting
            combined_output = f"""
ANALYSIS PROCESS
-------------------------------------------------------------------------------
{reasoning_content if reasoning_content else "No explicit reasoning process provided by the model."}

FINAL ASSESSMENT
-------------------------------------------------------------------------------
{final_content}
"""
            
            logger.info(f"Generated response with {len(reasoning_content) if reasoning_content else 0} chars of reasoning")
            return combined_output
            
        except Exception as e:
            logger.error(f"Error in DeepSeek API call: {str(e)}")
            
            # Fallback to direct API call if OpenAI client fails
            try:
                import requests
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature
                }
                
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code != 200:
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    return f"Error: API request failed with status {response.status_code}"
                
                result = response.json()
                # Apply clean formatting to fallback response too
                return f"""
ANALYSIS PROCESS
-------------------------------------------------------------------------------
No explicit reasoning process available from fallback API.

FINAL ASSESSMENT
-------------------------------------------------------------------------------
{result["choices"][0]["message"]["content"]}
"""
                
            except Exception as fallback_e:
                logger.error(f"Fallback API call also failed: {str(fallback_e)}")
                return f"Error in DeepSeek API call: {str(e)}\nFallback also failed: {str(fallback_e)}"

def process_company(company_file):
    """
    Process a single company file.
    
    Args:
        company_file (dict): Dictionary with company file information
        
    Returns:
        tuple: (success, output_file_path or None)
    """
    company_name = company_file['company_name']
    file_key = company_file['key']
    
    logger.info(f"Processing company: {company_name} (file: {file_key})")
    
    # Check if output already exists
    if check_output_exists(company_name):
        logger.info(f"Output for {company_name} already exists, skipping...")
        return (True, None)
    
    try:
        # Retrieve company info
        company_info = retrieve_company_info(file_key)
        
        # Create the reasoner
        reasoner = DeepSeekReasoner(
            model_id=MODEL_ID,
            temperature=TEMPERATURE
        )
        
        # Create the full prompt with the company information
        full_prompt = PROMPT.replace("{COMPANY_INFO}", company_info).replace("{COMPANY_NAME}", company_name)
        
        # Run the reasoning
        logger.info(f"Running reasoning on {company_name}")
        response = reasoner.generate(full_prompt)
        logger.info(f"Reasoning for {company_name} completed successfully")
        
        # Clean up the response format
        cleaned_response = clean_output_format(response)
        
        # Format the output for better readability
        formatted_output = f"""
==========================================================================
                       REASONING AGENT RESULTS
==========================================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {company_name}
Model: {MODEL_ID}
Temperature: {TEMPERATURE}
==========================================================================

{cleaned_response}

==========================================================================
Note: This assessment was automatically generated and should be reviewed
for accuracy by an investment professional.
==========================================================================
"""
        
        # Save the output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{company_name}_reasoning_result_{timestamp}.txt"
        
        with open(output_file, "w") as f:
            f.write(formatted_output)
        
        logger.info(f"Saved reasoning output for {company_name} to {output_file}")
        return (True, output_file)
        
    except Exception as e:
        logger.error(f"Error processing company {company_name}: {str(e)}")
        return (False, None)

def clean_output_format(text):
    """
    Clean the output format by removing asterisks and ensuring consistent formatting.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: The cleaned text
    """
    # Remove asterisks (bold markers)
    cleaned_text = text.replace("**", "")
    
    # Replace markdown headers with capitalized headers and separators
    cleaned_text = cleaned_text.replace("# Analysis Process", "ANALYSIS PROCESS\n-------------------------------------------------------------------------------")
    cleaned_text = cleaned_text.replace("# Final Assessment", "FINAL ASSESSMENT\n-------------------------------------------------------------------------------")
    
    # If these replacements didn't work (different casing), try alternatives
    if "# analysis process" in cleaned_text.lower() and "ANALYSIS PROCESS" not in cleaned_text:
        import re
        cleaned_text = re.sub(r'(?i)# analysis process.*?\n', "ANALYSIS PROCESS\n-------------------------------------------------------------------------------\n", cleaned_text)
        cleaned_text = re.sub(r'(?i)# final assessment.*?\n', "FINAL ASSESSMENT\n-------------------------------------------------------------------------------\n", cleaned_text)
    
    return cleaned_text

def main():
    """
    Main entry point for the reasoning agent.
    """
    logger.info("Starting multi-company reasoning agent")
    
    # List all company files
    company_files = list_company_files()
    
    if not company_files:
        logger.error("No company files found to process")
        return 1
    
    # Limit the number of companies to process if needed
    if len(company_files) > MAX_COMPANIES_TO_PROCESS:
        logger.warning(f"Limiting processing to {MAX_COMPANIES_TO_PROCESS} companies (found {len(company_files)})")
        company_files = company_files[:MAX_COMPANIES_TO_PROCESS]
    
    # Process each company
    successful = 0
    failed = 0
    skipped = 0
    
    for i, company_file in enumerate(company_files):
        logger.info(f"Processing company {i+1}/{len(company_files)}: {company_file['company_name']}")
        success, output_file = process_company(company_file)
        
        if success:
            if output_file:
                successful += 1
            else:
                skipped += 1
        else:
            failed += 1
    
    # Print summary
    logger.info(f"Multi-company processing complete. "
                f"Successful: {successful}, Failed: {failed}, Skipped: {skipped}")
    
    print(f"\nProcessing completed!")
    print(f"Successfully processed: {successful} companies")
    print(f"Failed to process: {failed} companies")
    print(f"Skipped (already processed): {skipped} companies")
    print(f"Results saved to: {output_dir}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
  

    