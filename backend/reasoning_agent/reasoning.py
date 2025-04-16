import os
import sys
import logging
import json
import concurrent.futures
from pathlib import Path
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from backend.reasoning_agent.prompts import PROMPT
from backend.reasoning_agent.config import (
    MODEL_ID, TEMPERATURE, OUTPUT_DIR, 
    S3_BUCKET, S3_REGION, S3_SUMMARIES_PREFIX,
    MAX_COMPANIES_TO_PROCESS, SKIP_EXISTING_OUTPUTS,
    NUM_REASONING_AGENTS, CONFIG
)
from langchain.schema import AgentAction, AgentFinish
from langchain_core.tools import BaseTool
from typing import Dict, List, Any, Optional, Type, ClassVar, Literal
from langchain_core.runnables import Runnable
from langchain_core.callbacks.manager import CallbackManagerForToolRun

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
                'size': obj['Size'],
                'processed': False,
                'success': None,
                'output_file': None,
                'error': None
            })
        
        logger.info(f"Found {len(company_files)} company files in S3")
        return company_files
        
    except Exception as e:
        logger.error(f"Error listing company files: {str(e)}")
        return []

def extract_company_name(filename):
    """
    Extract company name from filename (characters before first underscore).
    Skip 'www_' prefix if present to avoid duplicate company names.
    
    Args:
        filename (str): The filename
        
    Returns:
        str: The extracted company name
    """
    # Split by underscore and take the first part
    parts = filename.split('_')
    
    if not parts:
        return "unknown"  # Fallback if no underscore found
    
    # If the first part is "www" and there are more parts, use the second part
    if parts[0] == "www" and len(parts) > 1:
        return parts[1]  # Use the next part after "www_"
    
    # Otherwise use the first part as before
    return parts[0]

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

class DeepSeekReasoner:
    """
    A wrapper class for the DeepSeek Reasoning API.
    """
    def __init__(self, model_id=MODEL_ID, temperature=TEMPERATURE):
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

# Create standalone classes instead of extending BaseTool
class Reasoning:
    name = "reasoning"
    description = "Process company files to determine if they are potential buyers."
    
    def __init__(self, agent_id=0):
        self.agent_id = agent_id
        self.reasoner = DeepSeekReasoner(model_id=MODEL_ID, temperature=TEMPERATURE)
        logger.info(f"Initialized Reasoning agent {agent_id}")
    
    def __call__(self, companies, **kwargs):
        return self._run(companies)
    
    def _run(self, companies):
        """
        Process a list of companies.
        
        Args:
            companies: List of company dictionaries to process
            
        Returns:
            Dictionary with results and statistics
        """
        logger.info(f"Agent {self.agent_id} processing {len(companies)} companies")
        
        # Check if companies is not a list or is not a list of dictionaries
        if not isinstance(companies, list) or not companies or not isinstance(companies[0], dict):
            logger.warning(f"Agent {self.agent_id} received invalid companies data: {type(companies)}")
            return {
                "agent_id": self.agent_id,
                "results": [],
                "errors": [{"error": "Invalid companies data format"}],
                "stats": {"total": 0, "processed": 0, "successful": 0, "failed": 0, "skipped": 0}
            }
        
        results = []
        errors = []
        stats = {"total": len(companies), "processed": 0, "successful": 0, "failed": 0, "skipped": 0}
        
        for company in companies:
            company_name = company['company_name']
            file_key = company['key']
            
            # Check if this company should be skipped
            if check_output_exists(company_name):
                logger.info(f"Agent {self.agent_id}: Output already exists for {company_name}, skipping")
                stats["skipped"] += 1
                continue
            
            try:
                # Retrieve company info
                company_info = retrieve_company_info(file_key)
                
                # Create the full prompt with the company information
                full_prompt = PROMPT.replace("{COMPANY_INFO}", company_info).replace("{COMPANY_NAME}", company_name)
                
                # Run the reasoning
                logger.info(f"Agent {self.agent_id} running reasoning on {company_name}")
                response = self.reasoner.generate(full_prompt)
                
                # Clean up the response format
                cleaned_response = clean_output_format(response)
                
                # Format the output
                formatted_output = f"""
==========================================================================
                       REASONING AGENT RESULTS
==========================================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {company_name}
Model: {MODEL_ID}
Temperature: {TEMPERATURE}
Agent ID: {self.agent_id}
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
                
                logger.info(f"Agent {self.agent_id} saved output for {company_name} to {output_file}")
                
                results.append({
                    "company_name": company_name,
                    "file_key": file_key,
                    "output_file": str(output_file),
                    "success": True,
                    "agent_id": self.agent_id
                })
                
                stats["successful"] += 1
                
            except Exception as e:
                logger.error(f"Agent {self.agent_id} error processing {company_name}: {str(e)}")
                
                errors.append({
                    "company_name": company_name,
                    "file_key": file_key,
                    "error": str(e),
                    "agent_id": self.agent_id
                })
                
                stats["failed"] += 1
            
            stats["processed"] += 1
        
        logger.info(f"Agent {self.agent_id} completed processing with stats: {stats}")
        
        return {
            "agent_id": self.agent_id,
            "results": results,
            "errors": errors,
            "stats": stats
        }

class ReasoningOrchestrator:
    """
    LangGraph tool for orchestrating multiple DeepSeek reasoning agents.
    """
    name = "reasoning_orchestrator"
    description = "Orchestrate multiple reasoning agents to process company files in parallel."
    
    def __init__(self, llm: Optional[Runnable] = None):
        # Create agents
        self.agents = [Reasoning(agent_id=i) for i in range(NUM_REASONING_AGENTS)]
        
        logger.info(f"Initialized ReasoningOrchestrator with {len(self.agents)} agents")
    
    def __call__(self, urls: Optional[List[str]] = None, **kwargs):
        return self._run(urls)
    
    def _run(self, urls: Optional[List[str]] = None):
        """
        Orchestrate the processing of companies by multiple reasoning agents in parallel.
        """
        logger.info("Starting reasoning orchestration")
        
        # List all company files
        all_companies = list_company_files()
        
        if not all_companies:
            logger.warning("No company files found to process")
            return {
                "status": "complete",
                "message": "No company files found to process",
                "stats": {"total": 0, "processed": 0, "successful": 0, "failed": 0, "skipped": 0}
            }
        
        # Limit the number of companies if needed
        if len(all_companies) > MAX_COMPANIES_TO_PROCESS:
            logger.warning(f"Limiting processing to {MAX_COMPANIES_TO_PROCESS} companies")
            all_companies = all_companies[:MAX_COMPANIES_TO_PROCESS]
        
        # Distribute companies evenly among agents
        agent_assignments = [[] for _ in range(len(self.agents))]
        
        for i, company in enumerate(all_companies):
            agent_idx = i % len(self.agents)
            agent_assignments[agent_idx].append(company)
        
        logger.info(f"Distributed {len(all_companies)} companies among {len(self.agents)} agents")
        
        # Track statistics
        overall_stats = {
            "total": len(all_companies),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        
        all_results = []
        all_errors = []
        
        # Create a thread pool to run agents in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            # Submit tasks for each agent
            future_to_agent = {
                executor.submit(self._run_agent, i, agent, agent_assignments[i]): i 
                for i, agent in enumerate(self.agents) 
                if agent_assignments[i]  # Only submit if there are companies to process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_agent):
                agent_id = future_to_agent[future]
                try:
                    agent_results, agent_errors, agent_stats = future.result()
                    
                    # Merge results and errors
                    all_results.extend(agent_results)
                    all_errors.extend(agent_errors)
                    
                    # Update statistics
                    overall_stats["processed"] += agent_stats["processed"]
                    overall_stats["successful"] += agent_stats["successful"]
                    overall_stats["failed"] += agent_stats["failed"]
                    overall_stats["skipped"] += agent_stats["skipped"]
                    
                    logger.info(f"Agent {agent_id} completed processing with stats: {agent_stats}")
                    
                except Exception as e:
                    logger.error(f"Error running agent {agent_id}: {str(e)}")
                    # Count as failures
                    overall_stats["failed"] += len(agent_assignments[agent_id])
        
        logger.info(f"Parallel orchestration complete. Stats: {overall_stats}")
        
        return {
            "status": "complete",
            "results": all_results,
            "errors": all_errors,
            "stats": overall_stats,
            "reasoning_completed": True
        }

    def _run_agent(self, agent_id, agent, companies):
        """Helper method to run an agent and return results in the expected format"""
        if not companies:
            logger.info(f"Agent {agent_id} has no companies to process")
            return [], [], {"processed": 0, "successful": 0, "failed": 0, "skipped": 0}
        
        logger.info(f"Agent {agent_id} processing {len(companies)} companies in parallel thread")
        
        try:
            # Run the agent and get results
            agent_output = agent(companies)
            
            # Extract components
            results = agent_output.get("results", [])
            errors = agent_output.get("errors", [])
            stats = agent_output.get("stats", {})
            
            return results, errors, stats
            
        except Exception as e:
            logger.error(f"Unexpected error running agent {agent_id}: {str(e)}")
            return [], [{"error": str(e), "agent_id": agent_id}], {"processed": 0, "successful": 0, "failed": len(companies), "skipped": 0}

def reasoning_completion(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the completion of reasoning tasks.
    """
    logger.info("Processing reasoning completion")
    
    # Extract results from the state if they exist
    results = []
    stats = {"processed": 0, "successful": 0, "failed": 0, "skipped": 0}
    
    if "results" in state:
        results = state["results"]
    if "stats" in state:
        stats = state["stats"]
    
    # Log a summary of the results
    logger.info(f"Reasoning completed. "
                f"Processed: {stats.get('processed', 0)}, "
                f"Successful: {stats.get('successful', 0)}, "
                f"Failed: {stats.get('failed', 0)}, "
                f"Skipped: {stats.get('skipped', 0)}")
    
    # Generate a summary file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"reasoning_summary_{timestamp}.json"
    
    try:
        with open(summary_file, "w") as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"Saved reasoning summary to {summary_file}")
    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")
    
    # Return a clean state that won't trigger more processing
    # The key change is here - we return only necessary fields, not the full results
    return {
        "reasoning_completed": True,
        "summary_file": str(summary_file),
        "stats_summary": stats
    }

def main():
    """
    Main entry point for running the reasoning agent standalone (without graph).
    """
    logger.info("Starting reasoning orchestration")
    
    # Create orchestrator
    orchestrator = ReasoningOrchestrator()
    
    # Run orchestration
    result = orchestrator()
    
    # Process completion
    reasoning_completion(result)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
  

    