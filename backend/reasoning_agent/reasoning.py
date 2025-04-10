import os
import sys
import logging
import json
from pathlib import Path
import boto3
from datetime import datetime
from dotenv import load_dotenv
from backend.reasoning_agent.prompts import PROMPT
from backend.reasoning_agent.config import MODEL_ID, TEMPERATURE, OUTPUT_DIR

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
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        raise

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

def retrieve_company_info():
    """
    Retrieve the specific company summary from S3.
    
    Returns:
        str: The content of the summary file
    """
    s3_client = get_s3_client()
    bucket_name = "pe-profiles"  # Use your actual bucket name
    file_path = "Summaries/crescendocap_com_crescendo_summary_20250405_231050.txt"
    
    try:
        logger.info(f"Retrieving company info from S3: {file_path}")
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
        content = response['Body'].read().decode('utf-8')
        logger.info(f"Successfully retrieved {len(content)} characters of company data")
        return content
    except Exception as e:
        logger.error(f"Error retrieving file from S3: {str(e)}")
        # Provide a fallback for testing if S3 retrieval fails
        logger.warning("Using fallback test data since S3 retrieval failed")
        return "No company information available due to retrieval error."

def run_reasoning():
    """
    Run the reasoning agent on the company summary.
    
    Returns:
        str: The reasoning output
    """
    # Get the company information
    company_info = retrieve_company_info()
    
    # Create the reasoner with the specified model
    reasoner = DeepSeekReasoner(
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
        
        # Clean up the response format
        cleaned_response = clean_output_format(response)
        return cleaned_response
    except Exception as e:
        logger.error(f"Error during reasoning: {str(e)}")
        return f"Error during reasoning: {str(e)}"

def save_output(output):
    """
    Save the reasoning output to a file.
    
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

def clean_output_format(text):
    """
    Clean the output format by removing asterisks and ensuring consistent formatting.
    
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
Temperature: {TEMPERATURE}
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
  

    