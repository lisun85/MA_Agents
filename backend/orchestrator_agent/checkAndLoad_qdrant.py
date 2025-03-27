from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
import os
from dotenv import load_dotenv 

# Load environment variables
load_dotenv()

# Qdrant connection details
QDRANT_URL = "https://2c294842-b54a-4b7e-98e2-cc510d63dda5.us-east-1-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = os.getenv("QDRANT_API")
COLLECTION_NAME = "MA_Agent"

print(f"Using URL: {QDRANT_URL}")
print(f"API Key loaded: {'Yes' if QDRANT_API_KEY else 'No'}")
print(f"API Key (first few chars): {QDRANT_API_KEY[:10]}..." if QDRANT_API_KEY else "API Key not found")

# Initialize client
try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print("Successfully connected to Qdrant")
    
    # List collections
    collections = client.get_collections()
    print(f"Available collections: {[c.name for c in collections.collections]}")
    
    # Create collection if it doesn't exist
    if COLLECTION_NAME not in [c.name for c in collections.collections]:
        print(f"Creating collection '{COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print(f"Collection '{COLLECTION_NAME}' created successfully.")
    
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
            
            if "BASE CONTENT:" in content:
                base_content = content.split("BASE CONTENT:")[1].strip()
            else:
                base_content = content
            
            # Create metadata
            metadata = {
                "source": str(file_path),
                "url": url,
                "title": title,
                "company": "branfordcastle.com"
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
                    chunks.append(Document(page_content=chunk_content, metadata=chunk_metadata))
                
                documents.extend(chunks)
                print(f"Created {len(chunks)} chunks from {file_path}")
            else:
                # For smaller files, just add as a single document
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