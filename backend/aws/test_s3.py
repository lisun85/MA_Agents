import os
import sys
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the S3 client
from backend.aws.s3 import get_s3_client

def run_s3_tests():
    """Run tests for the S3 client functionality"""
    print("\n===== S3 CLIENT TEST =====\n")
    
    # Step 1: Initialize the client
    print("Initializing S3 client...")
    s3 = get_s3_client()
    
    if not s3:
        print("❌ Failed to initialize S3 client. Check your AWS credentials and .env file.")
        return
    
    print("✅ S3 client initialized successfully!")
    print(f"   Bucket name: {s3.bucket_name}")
    
    # Step 2: List directories and files
    print("\nListing files by directory...")
    try:
        files_by_directory = s3.list_files_by_directory()
        
        if not files_by_directory:
            print("⚠️ No files found in the bucket or an error occurred.")
        else:
            print(f"✅ Found {len(files_by_directory)} directories.")
            
            # Print directory structure
            for dir_name, files in files_by_directory.items():
                print(f"\n📁 Directory: {dir_name} ({len(files)} files)")
                # Print first 3 files as examples
                for i, file_path in enumerate(files[:3]):
                    print(f"   {i+1}. {file_path}")
                if len(files) > 3:
                    print(f"   ... and {len(files) - 3} more files")
            
            # Step 3: Test file content retrieval for a specific directory
            if files_by_directory:
                # Choose first directory with files for testing
                test_dir = next(iter(files_by_directory))
                print(f"\nTesting file content retrieval for directory: {test_dir}")
                contents = s3.get_files_content_by_directory(test_dir)
                
                if contents:
                    print(f"✅ Successfully retrieved {len(contents)} file contents.")
                    # Show preview of first file content
                    if len(contents) > 0:
                        print("\nPreview of first file content:")
                        preview = contents[0][:200] + "..." if len(contents[0]) > 200 else contents[0]
                        print(f"---\n{preview}\n---")
                else:
                    print("❌ Failed to retrieve file contents.")
                
                # Step 4: Test individual file content retrieval
                if files_by_directory[test_dir]:
                    test_file = files_by_directory[test_dir][0]
                    print(f"\nTesting individual file content retrieval: {test_file}")
                    file_content = s3.get_file_content(test_file)
                    
                    if file_content:
                        print(f"✅ Successfully retrieved file content.")
                        preview = file_content[:200] + "..." if len(file_content) > 200 else file_content
                        print(f"---\n{preview}\n---")
                    else:
                        print("❌ Failed to retrieve file content.")
    
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
    
    print("\n===== TEST COMPLETE =====")

if __name__ == "__main__":
    run_s3_tests() 