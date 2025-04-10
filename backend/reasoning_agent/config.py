"""
Reasoning Agent Configuration.

This module contains configuration settings for the reasoning agent.
"""

# Model configuration
MODEL_ID = "deepseek/deepseek-r1-zero:free"  # OpenRouter identifier for DeepSeek R1 Zero (free tier) from Chutes
# Alternative models
# MODEL_ID = "anthropic/claude-3.7-sonnet"
# MODEL_ID = "deepseek/deepseek-r1"

# Temperature - setting to None to use OpenRouter's default
TEMPERATURE = None

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_ENV_VAR = "OPENROUTER_API_KEY"
SITE_NAME = "PE Profiles Analyzer"
SITE_URL = "https://pe-profiles.com"  # Replace with your actual site URL

# S3 configuration
S3_BUCKET = "pe-profiles"
S3_REGION = "us-east-1"

# Output configuration
OUTPUT_DIR = "./output/reasoning_agent"