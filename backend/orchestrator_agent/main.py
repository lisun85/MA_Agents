from langchain_core.language_models import BaseLLM
import inspect
import logging
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from .tools import get_company_info
from langchain_core.prompts import ChatPromptTemplate
from .prompts import PROMPT

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_retrieval(query):
    """Test the retrieval process with a specific query"""
    logger.info(f"Testing retrieval for query: {query}")
    try:
        result = get_company_info(query)
        logger.info(f"Retrieval result length: {len(result)}")
        logger.info(f"Retrieval result preview: {result[:200]}...")
        return result
    except Exception as e:
        logger.error(f"Error during retrieval test: {str(e)}")
        return None

def test_end_to_end():
    """Test the end-to-end process of retrieving and generating a response"""
    print("\n--- Testing End-to-End Process ---")
    
    # Initialize LLM
    llm = ChatOpenAI(model_name="gpt-4-turbo", temperature=0)
    
    # Create prompt
    prompt = ChatPromptTemplate.from_template(PROMPT)
    prompt = prompt.partial(tools=[get_company_info])
    
    # Create chain
    chain = prompt | llm.bind_tools([get_company_info])
    
    # Test queries
    test_queries = [
        "What is Branford's portfolio?",
        "What companies has Branford invested in?",
        "What is Branford's media coverage?",
        "What is Branford's investment approach?"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: {query}")
        try:
            # First get the raw information
            info = get_company_info(query)
            print(f"Raw info length: {len(info)}")
            print(f"Raw info preview: {info[:150]}...")
            
            # Then test the full chain
            response = chain.invoke({"messages": [{"role": "user", "content": query}]})
            print(f"LLM response: {response.content}")
        except Exception as e:
            print(f"Error: {str(e)}")

def main():
    print("Hello from orchestrator-agent!")
    
    # Initialize LLM
    llm = ChatOpenAI(model_name="gpt-4-turbo", temperature=0)
    print(f"Using LLM model: {llm.model_name}")

    # Find all LLM instances in the current modules
    for name, obj in inspect.getmembers(globals()):
        if isinstance(obj, BaseLLM):
            print(f"Found LLM: {name}, Model: {obj.model_name}")
    
    # Test retrieval with different queries
    print("\n--- Testing Retrieval ---")
    test_queries = [
        "What is Branford's portfolio?",
        "What companies has Branford invested in?",
        "What is Branford's media coverage?",
        "What is Branford's investment approach?",
        "What is Branford's acquisition criteria?"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: {query}")
        result = test_retrieval(query)
        if result:
            print(f"Result snippet: {result[:150]}...")
        else:
            print("No result returned")

    # Add end-to-end test
    test_end_to_end()

if __name__ == "__main__":
    main()
