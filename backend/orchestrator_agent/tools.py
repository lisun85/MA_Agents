import os
import sys
from pathlib import Path
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.tools import tool

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import logging
import glob
from qdrant_client.http.models import Distance, VectorParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Qdrant connection details
QDRANT_URL = "https://2c294842-b54a-4b7e-98e2-cc510d63dda5.us-east-1-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = os.getenv("QDRANT_API")
COLLECTION_NAME = "MA_Agent"

# Make sure the API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set. Check your .env file at the project root.")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Flag to track if we're using the live retriever
using_live_retriever = False

def process_text_file(file_path):
    """Process a text file and extract content."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Extract URL and title if they exist
    url = None
    title = None
    base_content = content
    
    if "URL:" in content:
        url_line = content.split("URL:")[1].split("\n")[0].strip()
        url = url_line
    
    if "TITLE:" in content:
        title_line = content.split("TITLE:")[1].split("\n")[0].strip()
        title = title_line
    
    if "BASE CONTENT:" in content:
        base_content = content.split("BASE CONTENT:")[1].strip()
    
    # Create metadata
    metadata = {
        "source": str(file_path),
        "url": url,
        "title": title,
        "company": Path(file_path).parent.name  # Extract company name from directory
    }
    
    return Document(page_content=base_content, metadata=metadata)

def main():
    # Connect to Qdrant
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        logger.info(f"Connected to Qdrant at {QDRANT_URL}")
        
        # Check if collection exists, create it if it doesn't
        collections = qdrant_client.get_collections()
        if COLLECTION_NAME not in [c.name for c in collections.collections]:
            logger.info(f"Creating collection '{COLLECTION_NAME}'...")
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
        
        # Initialize vector store
        try:
            # Try the newer API format
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=COLLECTION_NAME,
                embedding=embeddings  # Changed from 'embeddings' to 'embedding'
            )
            logger.info("Successfully initialized QdrantVectorStore with 'embedding' parameter")
        except TypeError as e:
            logger.warning(f"Error with first method: {e}")
            # Try alternative API format
            from langchain.vectorstores import Qdrant
            vector_store = Qdrant(
                client=qdrant_client,
                collection_name=COLLECTION_NAME,
                embeddings=embeddings
            )
            logger.info("Successfully initialized Qdrant with alternative method")
        
        # Process text files
        # Adjust this path to where your files are located
        data_dir = Path("./data")  # Change this to your actual data directory
        
        # Option 1: Process specific files
        specific_files = [
            "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/investment-approach_what-makes-us-different.txt",
            "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/investment-approach.txt"
        ]
        
        documents = []
        for file_path in specific_files:
            if os.path.exists(file_path):
                logger.info(f"Processing file: {file_path}")
                doc = process_text_file(file_path)
                documents.append(doc)
            else:
                logger.warning(f"File not found: {file_path}")
        
        # Option 2: Process all files in a directory (uncomment to use)
        # file_pattern = str(data_dir / "**/*.txt")
        # for file_path in glob.glob(file_pattern, recursive=True):
        #     logger.info(f"Processing file: {file_path}")
        #     doc = process_text_file(file_path)
        #     documents.append(doc)
        
        # Add documents to vector store
        if documents:
            logger.info(f"Adding {len(documents)} documents to collection '{COLLECTION_NAME}'")
            vector_store.add_documents(documents)
            logger.info("Documents added successfully")
        else:
            logger.warning("No documents found to process")
        
        global using_live_retriever
        using_live_retriever = True
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.warning("Will fall back to mock retriever when querying")

if __name__ == "__main__":
    main()

@tool
def get_company_info(query: str) -> str:
    """
    Retrieve information about a company from the vector store
    
    Args:
        query: The query string to search for company information
        
    Returns:
        A string containing information about the company
    """
    try:
        logger.info(f"Searching for: {query}")
        
        # Use the Qdrant retriever to get relevant documents
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        try:
            # Try the newer API format
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=COLLECTION_NAME,
                embedding=embeddings  # Changed from 'embeddings' to 'embedding'
            )
            logger.info("Successfully initialized QdrantVectorStore with 'embedding' parameter")
        except TypeError as e:
            logger.warning(f"Error with first method: {e}")
            # Try alternative API format
            from langchain.vectorstores import Qdrant
            vector_store = Qdrant(
                client=qdrant_client,
                collection_name=COLLECTION_NAME,
                embeddings=embeddings
            )
            logger.info("Successfully initialized Qdrant with alternative method")
        
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        
        docs = retriever.get_relevant_documents(query)
        
        logger.info(f"Found {len(docs)} documents")
        for i, doc in enumerate(docs):
            logger.info(f"Doc {i+1} content: {doc.page_content[:100]}...")
            logger.info(f"Doc {i+1} metadata: {doc.metadata}")
        
        if docs:
            # Combine the content from the top documents
            result = "\n\n".join([doc.page_content for doc in docs])
            return result
        else:
            return f"No information found for query: {query}"
    except Exception as e:
        logger.error(f"Error retrieving company info: {str(e)}")
        # Fall back to mock implementation in case of errors
        return _mock_get_company_info(query)

def _mock_get_company_info(query: str) -> str:
    """Mock implementation for testing purposes"""
    if "Apple" in query:
        return "Apple Inc. is a technology company founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne."
    elif "Microsoft" in query:
        return "Microsoft Corporation is a technology company founded in 1975 by Bill Gates and Paul Allen."
    elif "Google" in query:
        return "Google LLC is a technology company founded in 1998 by Larry Page and Sergey Brin."
    elif "Amazon" in query:
        return "Amazon.com Inc. is an e-commerce and cloud computing company founded in 1994 by Jeff Bezos."
    elif "Facebook" in query or "Meta" in query:
        return "Facebook (now Meta Platforms, Inc.) is a social media company founded in 2004 by Mark Zuckerberg."
    else:
        return f"No specific information found for query: {query}. Please try a different company name."
