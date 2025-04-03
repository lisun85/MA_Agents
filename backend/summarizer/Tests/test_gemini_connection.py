import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Test connection to Google Gemini API."""
    # Load environment variables
    load_dotenv()
    
    # Get API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY not found in environment variables")
        return 1
    
    logger.info("Testing connection to Google Gemini 2.5 Pro Experimental")
    
    try:
        # Initialize the model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro-exp-03-25",
            temperature=0,
            google_api_key=google_api_key
        )
        
        # Test with a simple prompt
        test_prompt = "This is a connection test. Respond with 'Connection successful' only."
        response = llm.invoke(test_prompt)
        
        logger.info(f"Response received: {response.content}")
        logger.info("Connection test successful!")
        return 0
    
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 