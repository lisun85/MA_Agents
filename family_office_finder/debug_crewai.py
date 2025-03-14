#!/usr/bin/env python
"""
Debug script to check CrewAI Process options
"""

import os
import sys
import logging
from crewai import Process

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Check available Process options in CrewAI"""
    logger.info("Checking available Process options in CrewAI...")
    
    # Print all available Process options
    logger.info(f"Available Process options: {[attr for attr in dir(Process) if not attr.startswith('_')]}")
    
    # Print Process class details
    logger.info(f"Process class: {Process}")
    logger.info(f"Process class dir: {dir(Process)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 