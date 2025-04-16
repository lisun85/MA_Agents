"""
Reasoning Agent Configuration.

This module contains configuration settings for the reasoning agent.
"""

# Model configuration
MODEL_ID = "deepseek-reasoner"
TEMPERATURE = 1

# S3 configuration
S3_BUCKET = "pe-profiles"
S3_REGION = "us-east-1"
S3_SUMMARIES_PREFIX = "Summaries/"  # Prefix path for company summaries

# Output configuration
OUTPUT_DIR = "./backend/reasoning_agent/output"

# Batch processing configuration
MAX_COMPANIES_TO_PROCESS = 1000  # Limit to prevent processing too many files
SKIP_EXISTING_OUTPUTS = True   # Skip companies that already have output files

# Parallel processing configuration
NUM_REASONING_AGENTS = 6  # Number of parallel reasoning agents to use

# LangGraph Configuration
CONFIG = {
    "agent_size": NUM_REASONING_AGENTS,
    "urls": {
        "pe-profiles": "https://pe-profiles.com"
    },
    "default_values": {
        "sector": "finance",
        "check_size": "medium",
        "geographical_location": "US"
    }
}