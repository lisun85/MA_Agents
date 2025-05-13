"""
Email Agent Configuration.

This module contains configuration settings for the email agent.
"""
import os
from pathlib import Path

# Model configuration
MODEL_ID = "models/gemini-2.5-flash-preview-04-17"
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 4096

# API configuration
API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# File paths
REASONING_DIR = Path(os.path.expanduser("~/Documents/GitHub/MA_Agents/backend/reasoning_agent/output/7th_Run_TestRun_(Success)"))
OUTPUT_DIR = Path(os.path.expanduser("~/Documents/Github/MA_Agents/backend/email_agent/output"))

# Ensure the output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Filter settings
BUYER_PREFIX = "STRONG"

# Email template path with the new text file
EMAIL_TEMPLATE_PATH = Path(os.path.expanduser("~/Documents/GitHub/MA_Agents/backend/email_agent/template.txt"))

# Additional settings
LOG_LEVEL = "INFO"
MAX_EMAILS_TO_GENERATE = 1000  # Set a reasonable limit 