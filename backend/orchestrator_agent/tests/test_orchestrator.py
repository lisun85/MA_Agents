import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from dotenv import load_dotenv

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
from orchestrator import Orchestrator, orchestrator_action

# Note: orchestrator_router is not defined in the orchestrator.py file based on the context


class TestOrchestrator(unittest.TestCase):
    """
    Unit tests for the Orchestrator class
    """
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        orchestrator = Orchestrator(llm=MagicMock(), prompt=MagicMock())
        self.orchestrator = orchestrator
    
    def tearDown(self):
        """Clean up after each test method"""
        pass


class TestOrchestratorAction(unittest.TestCase):
    """
    Unit tests for the orchestrator_action function
    """
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        pass
    
    def tearDown(self):
        """Clean up after each test method"""
        pass


class TestOrchestratorRouter(unittest.TestCase):
    """
    Unit tests for the orchestrator_router function
    """
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        pass
    
    def tearDown(self):
        """Clean up after each test method"""
        pass


if __name__ == '__main__':
    unittest.main() 