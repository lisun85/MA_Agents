"""
LangGraph-based orchestration for parallel processing of company profiles.
"""
import os
import sys
import logging
import asyncio
from typing import List, Dict, Any, Annotated, TypedDict, Optional
from pathlib import Path
import time
import json
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import concurrent.futures

from backend.reasoning_agent.prompts import PROMPT
from backend.reasoning_agent.config import (
    MODEL_ID, TEMPERATURE, OUTPUT_DIR, 
    S3_BUCKET, S3_REGION, S3_SUMMARIES_PREFIX,
    MAX_COMPANIES_TO_PROCESS, SKIP_EXISTING_OUTPUTS,
    NUM_REASONING_AGENTS
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('reasoning_orchestrator.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure the output directory exists
output_dir = Path(OUTPUT_DIR)
output_dir.mkdir(parents=True, exist_ok=True)

# Define state schema for the orchestrator
class OrchestratorState(TypedDict):
    """State schema for the orchestration process."""
    all_company_files: List[Dict[str, Any]]
    agent_assignments: List[List[Dict[str, Any]]]
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    status: str
    stats: Dict[str, int]

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
    
    Returns:
        list: A list of dictionaries with company file information
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
    
    Args:
        filename (str): The filename
        
    Returns:
        str: The extracted company name
    """
    # Split by underscore and take the first part
    parts = filename.split('_')
    if parts:
        return parts[0]
    return "unknown"  # Fallback if no underscore found

def check_output_exists(company_name):
    """
    Check if an output file already exists for this company.
    
    Args:
        company_name (str): The company name to check
        
    Returns:
        bool: True if output exists, False otherwise
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
    
    Args:
        file_key (str): The S3 key for the company file
        
    Returns:
        str: The content of the summary file
        
    Raises:
        Exception: If the file cannot be retrieved
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

# Define the node functions for the graph

def initialize_orchestrator(state: OrchestratorState) -> OrchestratorState:
    """
    Initialize the orchestration process by scanning S3 and distributing work.
    """
    logger.info("Initializing orchestration process")
    
    # List all company files from S3
    all_company_files = list_company_files()
    
    if not all_company_files:
        logger.error("No company files found to process")
        return {
            "all_company_files": [],
            "agent_assignments": [],
            "results": [],
            "errors": [{"message": "No company files found to process"}],
            "status": "error",
            "stats": {"total": 0, "assigned": 0, "processed": 0, "successful": 0, "failed": 0, "skipped": 0}
        }
    
    # Limit the number of companies to process if needed
    if len(all_company_files) > MAX_COMPANIES_TO_PROCESS:
        logger.warning(f"Limiting processing to {MAX_COMPANIES_TO_PROCESS} companies (found {len(all_company_files)})")
        all_company_files = all_company_files[:MAX_COMPANIES_TO_PROCESS]
    
    # Filter out files that have already been processed if SKIP_EXISTING_OUTPUTS is True
    if SKIP_EXISTING_OUTPUTS:
        original_count = len(all_company_files)
        all_company_files = [
            file for file in all_company_files 
            if not check_output_exists(file['company_name'])
        ]
        skipped_count = original_count - len(all_company_files)
        logger.info(f"Skipping {skipped_count} files that already have output")
    
    # Distribute files evenly among agents
    num_agents = min(NUM_REASONING_AGENTS, len(all_company_files))
    agent_assignments = [[] for _ in range(num_agents)]
    
    for i, file in enumerate(all_company_files):
        agent_idx = i % num_agents
        agent_assignments[agent_idx].append(file)
    
    # Calculate statistics
    total_files = len(all_company_files)
    assigned_files = sum(len(assignment) for assignment in agent_assignments)
    
    logger.info(f"Distributed {assigned_files} files among {num_agents} agents")
    
    # Create the initial state
    return {
        "all_company_files": all_company_files,
        "agent_assignments": agent_assignments,
        "results": [],
        "errors": [],
        "status": "initialized",
        "stats": {
            "total": total_files,
            "assigned": assigned_files,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
    }

async def process_companies_parallel(state: OrchestratorState) -> OrchestratorState:
    """
    Process all companies in parallel using multiple agents.
    """
    logger.info("Starting parallel processing of companies")
    
    # Create a new state to avoid modifying the input state
    new_state = state.copy()
    results = []
    errors = []
    
    # Track statistics
    stats = {
        "total": state["stats"]["total"],
        "assigned": state["stats"]["assigned"],
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Create a thread pool for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_REASONING_AGENTS) as executor:
        # Submit a task for each agent
        future_to_agent = {
            executor.submit(process_agent_companies, 
                            agent_id=i, 
                            companies=assignments): i
            for i, assignments in enumerate(state["agent_assignments"])
        }
        
        # Process completed tasks as they finish
        for future in concurrent.futures.as_completed(future_to_agent):
            agent_id = future_to_agent[future]
            
            try:
                agent_results, agent_errors, agent_stats = future.result()
                logger.info(f"Agent {agent_id} completed processing with: "
                            f"{agent_stats['successful']} successful, "
                            f"{agent_stats['failed']} failed, "
                            f"{agent_stats['skipped']} skipped")
                
                # Merge results and errors
                results.extend(agent_results)
                errors.extend(agent_errors)
                
                # Update statistics
                stats["processed"] += agent_stats["processed"]
                stats["successful"] += agent_stats["successful"]
                stats["failed"] += agent_stats["failed"]
                stats["skipped"] += agent_stats["skipped"]
                
            except Exception as e:
                logger.error(f"Agent {agent_id} failed with error: {str(e)}")
                errors.append({
                    "agent_id": agent_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
    
    logger.info(f"Parallel processing complete. "
                f"Processed: {stats['processed']}, "
                f"Successful: {stats['successful']}, "
                f"Failed: {stats['failed']}, "
                f"Skipped: {stats['skipped']}")
    
    # Update the state
    new_state["results"] = results
    new_state["errors"] = errors
    new_state["stats"] = stats
    new_state["status"] = "completed"
    
    return new_state

def process_agent_companies(agent_id, companies):
    """
    Process a batch of companies assigned to a single agent.
    
    Args:
        agent_id (int): The ID of the agent
        companies (list): List of companies to process
        
    Returns:
        tuple: (results, errors, stats)
    """
    logger.info(f"Agent {agent_id} starting to process {len(companies)} companies")
    
    # Initialize DeepSeek reasoner for this agent
    from backend.reasoning_agent.reasoning import DeepSeekReasoner, clean_output_format
    
    reasoner = DeepSeekReasoner(
        model_id=MODEL_ID,
        temperature=TEMPERATURE
    )
    
    results = []
    errors = []
    stats = {
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Process each company
    for i, company in enumerate(companies):
        company_name = company['company_name']
        file_key = company['key']
        
        logger.info(f"Agent {agent_id} processing company {i+1}/{len(companies)}: {company_name}")
        
        # Check if output already exists
        if check_output_exists(company_name):
            logger.info(f"Output for {company_name} already exists, skipping...")
            stats["skipped"] += 1
            results.append({
                "company_name": company_name,
                "file_key": file_key,
                "status": "skipped",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
            continue
        
        try:
            # Retrieve company info
            company_info = retrieve_company_info(file_key)
            
            # Create the full prompt with the company information
            full_prompt = PROMPT.replace("{COMPANY_INFO}", company_info).replace("{COMPANY_NAME}", company_name)
            
            # Run the reasoning
            logger.info(f"Agent {agent_id} running reasoning on {company_name}")
            response = reasoner.generate(full_prompt)
            logger.info(f"Agent {agent_id} completed reasoning for {company_name}")
            
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
Agent ID: {agent_id}
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
            
            logger.info(f"Agent {agent_id} saved reasoning output for {company_name} to {output_file}")
            
            # Record the result
            results.append({
                "company_name": company_name,
                "file_key": file_key,
                "output_file": str(output_file),
                "status": "success",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            stats["successful"] += 1
            
        except Exception as e:
            error_msg = f"Error processing company {company_name}: {str(e)}"
            logger.error(f"Agent {agent_id}: {error_msg}")
            
            # Record the error
            errors.append({
                "company_name": company_name,
                "file_key": file_key,
                "error": str(e),
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            stats["failed"] += 1
        
        stats["processed"] += 1
    
    logger.info(f"Agent {agent_id} completed processing {len(companies)} companies")
    return results, errors, stats

def generate_summary(state: OrchestratorState) -> OrchestratorState:
    """
    Generate a summary of the processing results.
    """
    logger.info("Generating summary of processing results")
    
    # Create a new state to avoid modifying the input state
    new_state = state.copy()
    
    # Generate a summary file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"processing_summary_{timestamp}.json"
    
    # Prepare summary data
    summary_data = {
        "timestamp": datetime.now().isoformat(),
        "status": state["status"],
        "statistics": state["stats"],
        "results_count": len(state["results"]),
        "errors_count": len(state["errors"]),
        "successful_companies": [r["company_name"] for r in state["results"] if r["status"] == "success"],
        "failed_companies": [e["company_name"] for e in state["errors"]],
        "skipped_companies": [r["company_name"] for r in state["results"] if r["status"] == "skipped"]
    }
    
    # Save the summary
    try:
        with open(summary_file, "w") as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info(f"Saved processing summary to {summary_file}")
        
        # Print a summary to the console
        print(f"\nProcessing completed!")
        print(f"Total files: {state['stats']['total']}")
        print(f"Successfully processed: {state['stats']['successful']} companies")
        print(f"Failed to process: {state['stats']['failed']} companies")
        print(f"Skipped (already processed): {state['stats']['skipped']} companies")
        print(f"Results saved to: {output_dir}")
        print(f"Summary saved to: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")
    
    return new_state

def should_continue_processing(state: OrchestratorState) -> str:
    """
    Determine if the processing should continue or end.
    """
    # Processing is complete, go to summary generation
    if state["status"] == "initialized":
        return "process"
    elif state["status"] == "completed":
        return "summarize"
    else:
        return "end"

# Define the graph
def create_reasoning_graph():
    """
    Create a LangGraph workflow for orchestrating reasoning agents.
    """
    # Create workflow with state
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_orchestrator)
    workflow.add_node("process", process_companies_parallel)
    workflow.add_node("summarize", generate_summary)
    
    # Add edges
    workflow.add_conditional_edges(
        "initialize",
        should_continue_processing,
        {
            "process": "process",
            "summarize": "summarize",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "process",
        should_continue_processing,
        {
            "process": "process",
            "summarize": "summarize",
            "end": END
        }
    )
    
    workflow.add_edge("summarize", END)
    
    # Set the entry point
    workflow.set_entry_point("initialize")
    
    return workflow

# Create a compiled graph that can be executed
reasoning_orchestrator = create_reasoning_graph().compile()

def run_orchestrator():
    """
    Run the reasoning orchestrator.
    """
    logger.info("Starting reasoning orchestrator")
    result = reasoning_orchestrator.invoke({})
    logger.info("Reasoning orchestrator completed")
    return result

if __name__ == "__main__":
    run_orchestrator() 