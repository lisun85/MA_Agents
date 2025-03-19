import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from typing_extensions import Annotated
from typing import TypedDict
from langgraph.graph import add_messages
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
# Load environment variables before importing any modules that might need them
# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()

# Use only the root .env file (single source of truth)
env_path = PROJECT_ROOT / '.env'
if not env_path.exists():
    print(f"Warning: Environment file not found at {env_path}. Tests may fail.")
else:
    load_dotenv(env_path)
    print(f"Loaded environment variables from {env_path}")

# Import the modules to test
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.orchestrator_agent.orchestrator import Orchestrator, orchestrator_action

# Note: orchestrator_router is not defined in the orchestrator.py file based on the context
class State(TypedDict):
    messages: Annotated[list, add_messages]
    completed: bool

class TestOrchestrator(unittest.TestCase):
    """
    Unit tests for the Orchestrator class
    """
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        orchestrator = Orchestrator(llm=ChatOpenAI(model="gpt-4o-mini"))
        self.orchestrator = orchestrator
        graph = StateGraph(State)
        
        # Add the orchestrator node
        graph.add_node(Orchestrator.name, self.orchestrator)
        
        # Set the entry point
        graph.set_entry_point(Orchestrator.name)
        
        # Define conditional edge: if completed is True, end the graph
        graph.add_conditional_edges(
            Orchestrator.name,
            lambda state: END
        )
        
        # Compile the graph
        self.app = graph.compile(checkpointer=memory)
    
    def tearDown(self):
        """Clean up after each test method"""
        pass
    
    def test_orchestrator_no_query(self):
        """Test the Orchestrator initialization"""
   
        # Invoke the graph with proper initial state
        initial_state = {
            "messages": [HumanMessage(content="Hello, world!")]
        }
        
        # Run the test
        config = {"configurable": {"thread_id": "12"}}
        result = self.app.invoke(initial_state, config=config)
        
        # Verify the result
        self.assertIn("messages", result)
        self.assertTrue(len(result["messages"]) > 1)  # Should have added a response
        response = result["messages"][-1]
        self.assertIsInstance(response, AIMessage)
        # Assert that there are no tool calls in the AIMessage
        self.assertTrue(hasattr(response, "tool_calls") or not response.tool_calls)

    def test_orchestrator_with_query(self):
        """Test the Orchestrator with a query"""
        # Create a state graph with the proper state schema
        initial_state = {
            "messages": [HumanMessage(content="Hello, I want to know about Apple")]
        }   
        
        # Run the test
        config = {"configurable": {"thread_id": "123"}}
        result = self.app.invoke(initial_state, config=config)
        
        # Verify the result
        self.assertIn("messages", result)   
        self.assertTrue(len(result["messages"]) > 1)  # Should have added a response
        response = result["messages"][-1]
        self.assertIsInstance(response, AIMessage)
        # Assert that there are no tool calls in the AIMessage
        self.assertTrue(hasattr(response, "tool_calls") and len(response.tool_calls) > 0)
        
    def test_orchestrator_with_query_and_action(self):
        """Test the Orchestrator with a query and an action"""
        initial_state = {
            "messages": [HumanMessage(content="Hello, I want to know about Apple")]
        }   
        
        # Run the test
        config = {"configurable": {"thread_id": "1234"}}
        self.app.invoke(initial_state, config=config)
        state = self.app.get_state(config=config)
        print("STATE*****:", state.values)
        responses = orchestrator_action(state.values)
        tool_response = responses["messages"][-1]
        self.assertTrue('Apple' in tool_response.content)
        self.assertTrue('Content:' in tool_response.content)
        
        
if __name__ == '__main__':
    unittest.main() 