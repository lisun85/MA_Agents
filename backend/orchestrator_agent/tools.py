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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Make sure the API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set. Check your .env file at the project root.")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Set up Qdrant client
try:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_client = QdrantClient(url=qdrant_url)
    logger.info(f"Connected to Qdrant at {qdrant_url}")
    
    # Initialize vector store with our embeddings
    collection_name = "companies_info" # TODO make this set by environment variable
    
    # Try to get the collection, create it if it doesn't exist
    try:
        collections = qdrant_client.get_collections()
        if collection_name not in [c.name for c in collections.collections]:
            # Collection doesn't exist, create it
            from qdrant_client.http.models import Distance, VectorParams
            
            logger.info(f"Creating collection '{collection_name}'...")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            
            # Add sample data for demonstration
            sample_texts = [
                "Apple Inc. is a technology company founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne. "
                "It's known for products like iPhone, iPad, Mac computers, and services like Apple Music and iCloud.",
                
                "Microsoft Corporation is a technology company founded in 1975 by Bill Gates and Paul Allen. "
                "It's known for products like Windows, Office, Azure cloud services, and Xbox gaming consoles.",
                
                "Google LLC is a technology company founded in 1998 by Larry Page and Sergey Brin. "
                "It's known for its search engine, Android operating system, Chrome browser, Gmail, and YouTube.",
                
                "Amazon.com Inc. is an e-commerce and cloud computing company founded in 1994 by Jeff Bezos. "
                "It started as an online bookstore but now sells a wide variety of products and offers services like AWS.",
                
                "Facebook (now Meta Platforms, Inc.) is a social media company founded in 2004 by Mark Zuckerberg. "
                "It owns Instagram, WhatsApp, and Oculus VR, and is developing metaverse technologies."
            ]
            
            # Create Documents with metadata
            documents = []
            companies = ["Apple", "Microsoft", "Google", "Amazon", "Facebook"]
            
            for i, text in enumerate(sample_texts):
                doc = Document(
                    page_content=text,
                    metadata={"company": companies[i], "source": "sample data"}
                )
                documents.append(doc)
            
            # Initialize vector store to add documents
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=collection_name,
                embeddings=embeddings
            )
            
            # Add the documents to the collection
            vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} sample documents to collection '{collection_name}'")
    except Exception as e:
        logger.warning(f"Error when checking/creating collection: {str(e)}")
    
    # Initialize the vector store for retrieval
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embeddings
    )
    
    # Create a retriever
    retriever = vector_store.as_retriever()
    
    logger.info("Qdrant retriever initialized successfully")
    using_live_retriever = True
    
except Exception as e:
    logger.warning(f"Could not initialize Qdrant retriever: {str(e)}")
    logger.warning("Falling back to mock retriever")
    using_live_retriever = False

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
        if using_live_retriever:
            # Use the Qdrant retriever to get relevant documents
            docs = retriever.get_relevant_documents(query)
            
            if docs:
                # Combine the content from the top documents
                result = "\n\n".join([doc.page_content for doc in docs])
                return result
            else:
                return f"No information found for query: {query}"
        else:
            # Fall back to mock implementation
            return _mock_get_company_info(query)
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
