#!/usr/bin/env python
# src/ma_agents/main.py

import json
import os
from discover_agent.crew import MAAgentsCrew
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run():
    """
    Run the Discovery Agent to find potential buyers.
    """
    # Sample seed list and criteria
    inputs = {
        'seed_list': [
            "Vista Equity Partners",
            "Thoma Bravo",
            "Francisco Partners"
        ],
        'target_regions': "Chicago, IL",
        'min_aum': "$500 million",
        'target_industry': "Enterprise Software"
    }
    
    # Initialize the crew
    crew = MAAgentsCrew().crew()
    
    # Run the crew with the Discovery Agent
    result = crew.kickoff(inputs=inputs)
    
    # Process and store the results
    try:
        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the discovery results
        discovery_output = json.loads(result.raw)
        with open(f"{output_dir}/discovery_results.json", "w") as f:
            json.dump(discovery_output, f, indent=2)
        
        # Print a summary
        print("\n==========================================")
        print("DISCOVERY AGENT EXECUTION COMPLETED SUCCESSFULLY")
        print("==========================================")
        print(f"Discovered {len(discovery_output)} potential buyers")
        print(f"Results saved to {output_dir}/discovery_results.json")
        print("==========================================\n")
        
    except Exception as e:
        print(f"Error processing results: {e}")
        print(f"Raw result: {result.raw}")

if __name__ == "__main__":
    run()