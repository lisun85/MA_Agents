from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, Filter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
import os
from dotenv import load_dotenv 
import re

# Load environment variables
load_dotenv()

# Qdrant connection details
QDRANT_URL = "https://2c294842-b54a-4b7e-98e2-cc510d63dda5.us-east-1-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = os.getenv("QDRANT_API")
COLLECTION_NAME = "MA_Agent"

def clear_collection(client, collection_name):
    """
    Delete all points/payloads from the specified collection.
    If collection doesn't exist, it will be created fresh.
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection to clear
        
    Returns:
        bool: True if operation was successful, False otherwise
    """
    try:
        # Check if collection exists
        collections = client.get_collections()
        collection_exists = collection_name in [c.name for c in collections.collections]
        
        if collection_exists:
            print(f"Collection '{collection_name}' exists.")
            
            # Get current count
            count_before = client.count(collection_name=collection_name, exact=True)
            print(f"Points before deletion: {count_before.count}")
            
            if count_before.count > 0:
                # Delete all points in the collection
                print(f"Deleting all points from collection '{collection_name}'...")
                client.delete(
                    collection_name=collection_name,
                    points_selector=None  # None means delete all points
                )
                
                # Verify deletion
                count_after = client.count(collection_name=collection_name, exact=True)
                print(f"Points after deletion: {count_after.count}")
                
                if count_after.count == 0:
                    print(f"Successfully cleared all points from collection '{collection_name}'.")
                else:
                    print(f"Warning: {count_after.count} points still remain in the collection.")
            else:
                print(f"Collection '{collection_name}' is already empty.")
        else:
            print(f"Collection '{collection_name}' does not exist.")
            print(f"Creating new collection '{collection_name}'...")
            
            # Create new collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            print(f"Created new empty collection '{collection_name}'.")
        
        return True
        
    except Exception as e:
        print(f"Error clearing collection: {e}")
        
        # If there was an error, try to recreate the collection
        try:
            print(f"Attempting to recreate collection '{collection_name}'...")
            client.delete_collection(collection_name=collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            print(f"Collection '{collection_name}' recreated successfully.")
            return True
        except Exception as e2:
            print(f"Failed to recreate collection: {e2}")
            return False


# If this file is run directly (not imported), execute this code
if __name__ == "__main__":
    print(f"Using URL: {QDRANT_URL}")
    print(f"API Key loaded: {'Yes' if QDRANT_API_KEY else 'No'}")
    print(f"API Key (first few chars): {QDRANT_API_KEY[:10]}..." if QDRANT_API_KEY else "API Key not found")

    try:
        # Initialize client
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("Successfully connected to Qdrant")
        
        # Clear the collection before processing files
        if clear_collection(client, COLLECTION_NAME):
            print("Collection cleared successfully. Ready to process and upload new documents.")
            
            # Continue with the rest of your code for processing and uploading documents
            # 2. Check collection info
            collection_info = client.get_collection(collection_name=COLLECTION_NAME)
            print(f"\nCollection info: {collection_info}")

            # 3. Count points in collection
            count = client.count(collection_name=COLLECTION_NAME, exact=True)
            print(f"\nNumber of points in collection: {count.count}")

            # Initialize embeddings
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

            # Process and upload the Branford Castle documents
            file_paths = [
                # Original files
                "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/investment-approach_what-makes-us-different.txt",
                "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/investment-approach.txt",
                # New files
                "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/media-coverage.txt",
                "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/investment-approach_acquisition-criteria.txt",
                "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/portfolio.txt",
                "/Users/lisun/Library/CloudStorage/GoogleDrive-lisun08@gmail.com/My Drive/AgentPE/Scraped_Buyers/data/Batch1/branfordcastle.com/team.txt"
            ]

            # Function to determine document type based on filename and content
            def determine_document_type(file_path, content):
                file_name = os.path.basename(file_path).lower()
                
                # Check filename for patterns
                if any(term in file_name for term in ["portfolio", "companies", "investments"]):
                    return "list of portfolio companies"
                elif "team" in file_name:
                    return "team"
                elif "media" in file_name:
                    return "media"
                elif "contact" in file_name:
                    return "contacts"
                elif any(term in file_name for term in ["investment-approach", "acquisition-criteria", "criteria", "approach"]):
                    return "investment approach & criteria"
                
                # Secondary check based on content if filename is not definitive
                content_lower = content.lower()
                
                # More robust portfolio detection
                portfolio_indicators = [
                    # Common section headers
                    "portfolio companies", "our portfolio", "current investments", "realized investments", 
                    "our companies", "select investments", "active investments",
                    
                    # Common investment types
                    "management buyout", "family succession", "recapitalization", "founder/owner managed",
                    
                    # Status indicators
                    "exited", "realized", "current", "active", "acquired",
                    
                    # Formatting patterns that appear in portfolio listings
                    "founded in" in content_lower and ("acquired" in content_lower or "headquarters" in content_lower),
                    
                    # Multiple company indicators
                    len(re.findall(r'(inc\.|llc|corp\.?|company|www\.[a-z0-9-]+\.com)', content_lower)) > 3
                ]
                
                if any(indicator in content_lower for indicator in portfolio_indicators if isinstance(indicator, str)) or any(indicator for indicator in portfolio_indicators if isinstance(indicator, bool) and indicator):
                    return "list of portfolio companies"
                
                elif any(term in content_lower for term in ["team", "leadership", "management", "executive"]):
                    return "team"
                elif any(term in content_lower for term in ["press", "news", "media"]):
                    return "media"
                elif any(term in content_lower for term in ["contact", "email", "phone", "reach"]):
                    return "contacts"
                elif any(term in content_lower for term in ["investment criteria", "acquisition criteria", "investment approach", 
                                                          "investment strategy", "what we look for", "target companies"]):
                    return "investment approach & criteria"
                
                # Default to a generic type
                return "company information"

            # Function to generate a summary for the chunk
            def generate_summary(content, doc_type, title):
                # Truncate content for summary generation
                summary_content = content[:2000] if len(content) > 2000 else content
                
                if doc_type == "list of portfolio companies":
                    # Extract company names more effectively
                    company_names = []
                    
                    # Try to find company names with pattern matching
                    # Common patterns: 
                    # 1. Line starts with a company name followed by description
                    # 2. Headers or bold text containing company names
                    # 3. Companies followed by "Founded in" or "Acquired in"
                    
                    # Look for lines that likely contain company names
                    lines = summary_content.split('\n')
                    potential_companies = []
                    
                    for line in lines:
                        line = line.strip()
                        # Skip empty lines and common non-company lines
                        if not line or line.startswith("URL:") or line.startswith("TITLE:") or line.startswith("==="):
                            continue
                            
                        # Look for standalone company names (short lines that aren't navigation items)
                        if len(line) < 50 and not any(nav in line.lower() for nav in ["home", "about", "contact", "news", "approach"]):
                            potential_companies.append(line)
                        
                        # Look for lines with company names followed by descriptions
                        elif "inc." in line.lower() or "llc" in line.lower() or "corp" in line.lower():
                            # Extract company name from beginning of line
                            match = re.search(r'^([^\.,:]+)[\.,:]', line)
                            if match:
                                potential_companies.append(match.group(1).strip())
                        
                        # Look for "Founded in" patterns
                        elif "founded in" in line.lower() and len(potential_companies) > 0:
                            # The previous line might be a company name
                            if potential_companies[-1] not in company_names:
                                company_names.append(potential_companies[-1])
                    
                    # If we found potential companies but not confirmed, add some potential ones
                    if not company_names and potential_companies:
                        # Take all potential companies instead of just the first 5
                        company_names = [company for company in potential_companies if len(company) < 50]
                    
                    # If we still don't have companies, fall back to lines that might be companies
                    if not company_names:
                        # Find all short lines that might be company names, not just the first 5
                        company_names = [line.strip() for line in lines if line.strip() and len(line.strip()) < 50 
                                       and not line.strip().startswith("URL:") and not line.strip().startswith("TITLE:")
                                       and not any(common in line.lower() for common in ["copyright", "home", "about", "contact", "all rights"])]
                    
                    # Create the summary
                    company_count = len(company_names)
                    if company_count > 0:
                        # Display up to 3 company names as examples in the summary
                        display_names = company_names[:3]
                        return f"Portfolio listing containing {company_count} companies including {', '.join(display_names)} and others"
                    
                    # Fallback if no company names found
                    return f"List of portfolio companies and investments for {title.split('–')[1].strip() if '–' in title else title}"
                    
                elif doc_type == "team":
                    return f"Information about the team members and leadership at {title.split('–')[1].strip() if '–' in title else title}"
                    
                elif doc_type == "media":
                    return f"Media coverage and press releases related to {title.split('–')[1].strip() if '–' in title else title}"
                    
                elif doc_type == "contacts":
                    return f"Contact information and details for {title.split('–')[1].strip() if '–' in title else title}"
                    
                elif doc_type == "investment approach & criteria":
                    # Look for key indicators in content to create a more specific summary
                    key_criteria = []
                    if "revenue" in summary_content.lower() or "ebitda" in summary_content.lower():
                        for line in summary_content.lower().split('\n'):
                            if any(term in line for term in ["revenue", "ebitda", "$", "million", "growth"]):
                                key_criteria.append(line.strip())
                    
                    if key_criteria and len(key_criteria) <= 3:
                        criteria_text = "; ".join(key_criteria)
                        return f"Investment approach and acquisition criteria including: {criteria_text}"
                    else:
                        return f"Information about investment approach, strategy and acquisition criteria for {title.split('–')[1].strip() if '–' in title else title}"
                
                # Generic summary
                words = summary_content.split()
                relevant_words = words[:30]  # Take first 30 words for summary
                summary = ' '.join(relevant_words)
                return f"{summary}..." if len(words) > 30 else summary

            # Check if files exist
            documents = []
            for file_path in file_paths:
                if os.path.exists(file_path):
                    print(f"Processing file: {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        
                    # Extract metadata
                    url = None
                    title = None
                    if "URL:" in content:
                        url_line = content.split("URL:")[1].split("\n")[0].strip()
                        url = url_line
                    
                    if "TITLE:" in content:
                        title_line = content.split("TITLE:")[1].split("\n")[0].strip()
                        title = title_line
                    else:
                        title = os.path.basename(file_path).replace(".txt", "").replace("_", " ").title()
                    
                    if "BASE CONTENT:" in content:
                        base_content = content.split("BASE CONTENT:")[1].strip()
                    else:
                        base_content = content
                    
                    # Determine document type
                    doc_type = determine_document_type(file_path, base_content)
                    
                    # Create metadata
                    metadata = {
                        "source": str(file_path),
                        "url": url,
                        "title": title,
                        "company": "branfordcastle.com",
                        "type": doc_type,
                    }
                    
                    # For large files like media-coverage.txt, split into chunks
                    if len(base_content) > 8000:  # If content is large
                        print(f"Chunking large file: {file_path}")
                        # Split by paragraphs or sections
                        chunks = []
                        lines = base_content.split('\n')
                        current_chunk = []
                        current_length = 0
                        
                        for line in lines:
                            if current_length + len(line) > 4000 and current_length > 0:
                                # Create a document from the current chunk
                                chunk_content = '\n'.join(current_chunk)
                                chunk_metadata = metadata.copy()
                                chunk_metadata["chunk"] = len(chunks) + 1
                                
                                # Generate and add summary for this chunk
                                chunk_metadata["summary"] = generate_summary(chunk_content, doc_type, title)
                                
                                chunks.append(Document(page_content=chunk_content, metadata=chunk_metadata))
                                
                                # Start a new chunk
                                current_chunk = [line]
                                current_length = len(line)
                            else:
                                current_chunk.append(line)
                                current_length += len(line)
                        
                        # Add the last chunk if it's not empty
                        if current_chunk:
                            chunk_content = '\n'.join(current_chunk)
                            chunk_metadata = metadata.copy()
                            chunk_metadata["chunk"] = len(chunks) + 1
                            
                            # Generate and add summary for the last chunk
                            chunk_metadata["summary"] = generate_summary(chunk_content, doc_type, title)
                            
                            chunks.append(Document(page_content=chunk_content, metadata=chunk_metadata))
                        
                        documents.extend(chunks)
                        print(f"Created {len(chunks)} chunks from {file_path}")
                    else:
                        # For smaller files, just add as a single document
                        metadata["summary"] = generate_summary(base_content, doc_type, title)
                        documents.append(Document(page_content=base_content, metadata=metadata))
                else:
                    print(f"File not found: {file_path}")

            # Upload documents if we have any
            if documents:
                print(f"Uploading {len(documents)} documents to Qdrant...")
                try:
                    # Try the newer API format
                    vector_store = QdrantVectorStore(
                        client=client,
                        collection_name=COLLECTION_NAME,
                        embedding=embeddings
                    )
                    vector_store.add_documents(documents)
                    print("Documents uploaded successfully.")
                except TypeError as e:
                    print(f"Error with first method: {e}")
                    try:
                        # Try alternative API format
                        from langchain.vectorstores import Qdrant
                        vector_store = Qdrant(
                            client=client,
                            collection_name=COLLECTION_NAME,
                            embeddings=embeddings
                        )
                        vector_store.add_documents(documents)
                        print("Documents uploaded successfully with alternative method.")
                    except Exception as e2:
                        print(f"Error with alternative method: {e2}")

            # 4. Try a direct search
            query_vector = embeddings.embed_query("Branford Castle acquisition criteria")

            search_results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=3
            )

            print("\nSearch results:")
            for result in search_results:
                print(f"Score: {result.score}")
                print(f"Payload: {result.payload}")
                print("---")

            # 5. Scroll through some points to see what's actually stored
            print("\nSample points in collection:")
            points = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=2,
                with_payload=True,
                with_vectors=False
            )[0]

            for point in points:
                print(f"ID: {point.id}")
                print(f"Payload: {point.payload}")
                print("---")

    except Exception as e:
        print(f"Error connecting to Qdrant: {str(e)}")