from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os
from checkAndLoad_qdrant import clear_collection

# Load environment variables
load_dotenv()

# Qdrant connection details
QDRANT_URL = "https://2c294842-b54a-4b7e-98e2-cc510d63dda5.us-east-1-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = os.getenv("QDRANT_API")
COLLECTION_NAME = "MA_Agent"

if __name__ == "__main__":
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("Successfully connected to Qdrant")
        
        # Clear the collection
        success = clear_collection(client, COLLECTION_NAME)
        
        if success:
            print(f"Collection '{COLLECTION_NAME}' has been successfully cleared.")
        else:
            print(f"Failed to clear collection '{COLLECTION_NAME}'.")
            
    except Exception as e:
        print(f"Error: {e}") 