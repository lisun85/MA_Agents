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
    OPENROUTER_BASE_URL, OPENROUTER_API_ENV_VAR,
    SITE_NAME, SITE_URL, S3_BUCKET, S3_REGION
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

def test_s3_connection():
    """
    Test the S3 connection and bucket access.
    Returns True if successful, False otherwise.
    """
    try:
        s3_client = get_s3_client()
        
        # Test if we can list objects in the bucket
        s3_client.list_objects_v2(Bucket=S3_BUCKET, MaxKeys=1)
        logger.info(f"Successfully connected to S3 bucket: {S3_BUCKET}")
        
        return True
    except ClientError as e:
        logger.error(f"S3 connection test failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during S3 connection test: {str(e)}")
        return False

def check_s3_file_exists(bucket, key):
    """
    Check if a file exists in the S3 bucket.
    
    Args:
        bucket: The S3 bucket name
        key: The file path/key in the bucket
        
    Returns:
        bool: True if the file exists, False otherwise
    """
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=bucket, Key=key)
        logger.info(f"File exists in S3: {bucket}/{key}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.warning(f"File does not exist in S3: {bucket}/{key}")
        else:
            logger.error(f"Error checking if file exists in S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking if file exists in S3: {str(e)}")
        return False

def retrieve_company_info():
    """
    Retrieve the specific company summary from S3.
    Returns the content of the file if successful, or raises an exception if all attempts fail.
    
    Returns:
        str: The content of the summary file
    
    Raises:
        Exception: If the file cannot be retrieved from any path
    """
    bucket_name = S3_BUCKET
    file_path = "Summaries/crescendocap_com_crescendo_summary_20250405_231050.txt"
    
    # First check if the file exists
    if check_s3_file_exists(bucket_name, file_path):
        try:
            s3_client = get_s3_client()
            logger.info(f"Retrieving company info from S3: {file_path}")
            response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully retrieved {len(content)} characters of company data")
            return content
        except Exception as e:
            logger.error(f"Error retrieving file from S3: {str(e)}")
            raise Exception(f"Failed to retrieve {file_path} from S3: {str(e)}")
    else:
        # Try alternative paths
        alternative_paths = [
            "summaries/crescendocap_com_crescendo_summary_20250405_231050.txt",  # lowercase
            "Summaries/crescendocap.txt",
            "summaries/crescendocap.txt",
            "crescendocap_com_crescendo_summary.txt",
            "crescendocap.txt"
        ]
        
        for alt_path in alternative_paths:
            if check_s3_file_exists(bucket_name, alt_path):
                try:
                    s3_client = get_s3_client()
                    logger.info(f"Retrieving company info from alternative S3 path: {alt_path}")
                    response = s3_client.get_object(Bucket=bucket_name, Key=alt_path)
                    content = response['Body'].read().decode('utf-8')
                    logger.info(f"Successfully retrieved {len(content)} characters of company data from alternative path")
                    return content
                except Exception as e:
                    logger.error(f"Error retrieving file from alternative S3 path: {str(e)}")
                    # Continue trying other paths
        
        # If we get here, all attempts have failed
        tried_paths = [file_path] + alternative_paths
        error_msg = f"Failed to retrieve company data from any path in S3. Attempted paths: {', '.join(tried_paths)}"
        logger.error(error_msg)
        raise Exception(error_msg)

class ModelReasoner:
    """
    A wrapper class for accessing LLMs via OpenRouter API.
    """
    def __init__(self, model_id, temperature=0):
        self.model_id = model_id
        self.temperature = temperature
        # Get API key from environment variables
        self.api_key = os.getenv(OPENROUTER_API_ENV_VAR)
        if not self.api_key:
            raise ValueError(f"{OPENROUTER_API_ENV_VAR} not found in .env file. Please add it to your .env file.")
        logger.info(f"Initialized ModelReasoner with model: {model_id} via OpenRouter")
        
    def generate(self, prompt):
        """
        Generate a response using the selected model via OpenRouter API.
        Uses direct requests for better reliability.
        """
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            }
            
            # Base request data
            data = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "route": "chutes"  # Specify the Chutes provider
            }
            
            # Only add temperature if it's not None
            if self.temperature is not None:
                data["temperature"] = self.temperature
            
            # Model-specific configurations for DeepSeek R1 models
            if "deepseek-r1" in self.model_id.lower():
                data["reasoning"] = {
                    "effort": "high",
                    "exclude": False  # Include reasoning in the response
                }
            
            response = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return f"Error: API request failed with status {response.status_code}"
            
            result = response.json()
            
            # Extract reasoning content if available
            reasoning_content = ""
            try:
                if "reasoning" in result['choices'][0]['message']:
                    reasoning_content = result['choices'][0]['message']['reasoning']
                    logger.info(f"Model provided {len(reasoning_content)} chars of reasoning")
            except (KeyError, IndexError) as e:
                logger.warning(f"Could not extract reasoning content: {str(e)}")
            
            # Extract the final content
            final_content = result['choices'][0]['message']['content']
            
            # If reasoning is available and we want to include it
            if reasoning_content:
                combined_output = f"""
REASONING:
{reasoning_content}

FINAL ANSWER:
{final_content}
"""
                return combined_output
            else:
                return final_content
                
        except Exception as e:
            logger.error(f"Error in OpenRouter API call: {str(e)}")
            return f"Error in OpenRouter API call: {str(e)}"

def run_reasoning():
    """
    Run the reasoning agent on the company summary.
    
    Returns:
        str: The reasoning output or an error message
    """
    # First, test S3 connection
    if not test_s3_connection():
        error_msg = "S3 connection test failed. Cannot retrieve company information."
        logger.error(error_msg)
        return f"ERROR: {error_msg}"
    
    try:
        # Get the company information - this will now raise an exception if it fails
        company_info = retrieve_company_info()
        
        # Create the reasoner with the specified model
        reasoner = ModelReasoner(
            model_id=MODEL_ID,
            temperature=TEMPERATURE
        )
        
        # Create the full prompt with the company information
        full_prompt = PROMPT.replace("{COMPANY_INFO}", company_info)
        
        # Run the reasoning
        logger.info("Running reasoning on company information")
        try:
            response = reasoner.generate(full_prompt)
            logger.info("Reasoning completed successfully")
            return response
        except Exception as e:
            error_msg = f"Error during reasoning: {str(e)}"
            logger.error(error_msg)
            return f"ERROR: {error_msg}"
            
    except Exception as e:
        error_msg = f"Failed to retrieve company information: {str(e)}"
        logger.error(error_msg)
        return f"ERROR: {error_msg}"

def save_output(output):
    """
    Save the reasoning output to a file.
    
    Args:
        output (str): The reasoning output to save
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"reasoning_result_{timestamp}.txt"
    
    try:
        with open(output_file, "w") as f:
            f.write(output)
        logger.info(f"Saved reasoning output to {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error saving output: {str(e)}")
        return None

def main():
    """
    Main entry point for the reasoning agent.
    """
    logger.info("Starting reasoning agent")
    
    # Run the reasoning
    output = run_reasoning()
    
    # Format the output for better readability
    formatted_output = f"""
==========================================================================
                       REASONING AGENT RESULTS
==========================================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Model: {MODEL_ID}
Temperature: {TEMPERATURE if TEMPERATURE is not None else "Default (OpenRouter recommended)"}
==========================================================================

{output}

==========================================================================
Note: This assessment was automatically generated and should be reviewed
for accuracy by an investment professional.
==========================================================================
"""
    
    # Save the output
    output_file = save_output(formatted_output)
    
    # Print a summary to console
    if output_file:
        print(f"\nReasoning completed successfully!")
        print(f"Output saved to: {output_file}")
    else:
        print("\nReasoning completed but there was an error saving the output.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
  

    