import os
import sys
from pathlib import Path
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Load the .env file from the project root (single source of truth)
env_path = PROJECT_ROOT / '.env'
if not env_path.exists():
    raise FileNotFoundError(f"Environment file not found at {env_path}. Please create it.")

load_dotenv(env_path)
print(f"Loaded environment variables from {env_path}")

# Make sure the API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set. Check your .env file at the project root.")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# For testing, we'll use mock functions instead of trying to connect to Qdrant
def get_company_info(query: str) -> str:
    """
    Retrieve information about a company from the vector store
    
    For testing purposes, this returns mock responses based on the query.
    """
    # Simple mock implementation that returns different responses based on the query
    if "Apple" in query:
        return "Apple Inc. is a technology company founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne."
    elif "Microsoft" in query:
        return "Microsoft Corporation is a technology company founded in 1975 by Bill Gates and Paul Allen."
    elif "Google" in query:
        return "Google LLC is a technology company founded in 1998 by Larry Page and Sergey Brin."
    else:
        return f"No specific information found for query: {query}. Please try a different company name."
