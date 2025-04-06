#!/usr/bin/env python
"""
Team Manager for Summarizer Agents.

This script runs three separate teams of summarizer agents in parallel,
each processing its own batch of directories.
"""

import os
import sys
import argparse
import subprocess
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('teams_manager.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
TEAM1_DIRS_FILE = "batch1_directories.txt"
TEAM2_DIRS_FILE = "batch2_directories.txt"
TEAM3_DIRS_FILE = "batch3_directories.txt"
TEAM1_NAME = "Team1"
TEAM2_NAME = "Team2"
TEAM3_NAME = "Team3"
DEFAULT_OUTPUT_DIR = "output"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run multiple teams of summarizer agents")
    
    parser.add_argument(
        "--team1-workers", 
        type=int, 
        default=4,
        help="Number of workers for Team 1 (default: 4)"
    )
    parser.add_argument(
        "--team2-workers", 
        type=int, 
        default=4,
        help="Number of workers for Team 2 (default: 4)"
    )
    parser.add_argument(
        "--team3-workers", 
        type=int, 
        default=4,
        help="Number of workers for Team 3 (default: 4)"
    )
    parser.add_argument(
        "--parallel", "-p", 
        action="store_true",
        help="Use parallel extraction for faster processing within each directory"
    )
    parser.add_argument(
        "--output-dir", "-o", 
        default=DEFAULT_OUTPUT_DIR,
        help=f"Base output directory for summaries (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    
    return parser.parse_args()

def run_team(team_name, dirs_file, num_workers, parallel, output_dir, debug):
    """
    Run a team of summarizer agents on a batch of directories.
    
    Args:
        team_name: Name of the team
        dirs_file: File containing directories to process
        num_workers: Number of workers (agents) in the team
        parallel: Whether to use parallel extraction
        output_dir: Directory to save output files
        debug: Whether to enable debug mode
    
    Returns:
        Dictionary with team results
    """
    logger.info(f"Starting {team_name} with {num_workers} workers")
    
    # Get the path to the run_multi_directories.py script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    run_script = os.path.join(script_dir, "run_multi_directories.py")
    
    # Create team-specific output directory
    team_output_dir = os.path.join(output_dir, team_name)
    os.makedirs(team_output_dir, exist_ok=True)
    
    # Build command for running the team
    cmd = [
        "python", 
        run_script,
        "--team-name", team_name,
        "--dirs-file", dirs_file,
        "--max-workers", str(num_workers),
        "--output-dir", team_output_dir
    ]
    
    if parallel:
        cmd.append("--parallel")
    
    if debug:
        cmd.append("--debug")
    
    # Log the command
    logger.info(f"{team_name} command: {' '.join(cmd)}")
    
    # Run the command
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            logger.info(f"{team_name} completed successfully in {duration:.2f} seconds")
            success = True
        else:
            logger.error(f"{team_name} failed: {result.stderr}")
            success = False
        
        return {
            "team_name": team_name,
            "success": success,
            "duration": duration,
            "output": result.stdout,
            "error": result.stderr
        }
    
    except Exception as e:
        logger.error(f"Error running {team_name}: {str(e)}")
        return {
            "team_name": team_name,
            "success": False,
            "error": str(e)
        }

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run all teams in parallel
    logger.info("Starting all teams in parallel")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit team tasks
        team1_future = executor.submit(
            run_team, 
            TEAM1_NAME, 
            TEAM1_DIRS_FILE, 
            args.team1_workers, 
            args.parallel, 
            args.output_dir, 
            args.debug
        )
        
        team2_future = executor.submit(
            run_team, 
            TEAM2_NAME, 
            TEAM2_DIRS_FILE, 
            args.team2_workers, 
            args.parallel, 
            args.output_dir, 
            args.debug
        )
        
        team3_future = executor.submit(
            run_team, 
            TEAM3_NAME, 
            TEAM3_DIRS_FILE, 
            args.team3_workers, 
            args.parallel, 
            args.output_dir, 
            args.debug
        )
        
        # Get results
        team1_result = team1_future.result()
        team2_result = team2_future.result()
        team3_result = team3_future.result()
    
    # Report results
    logger.info("All teams completed")
    
    logger.info(f"{TEAM1_NAME}: {'Success' if team1_result['success'] else 'Failed'}")
    if 'duration' in team1_result:
        logger.info(f"{TEAM1_NAME} duration: {team1_result['duration']:.2f} seconds")
    
    logger.info(f"{TEAM2_NAME}: {'Success' if team2_result['success'] else 'Failed'}")
    if 'duration' in team2_result:
        logger.info(f"{TEAM2_NAME} duration: {team2_result['duration']:.2f} seconds")
    
    logger.info(f"{TEAM3_NAME}: {'Success' if team3_result['success'] else 'Failed'}")
    if 'duration' in team3_result:
        logger.info(f"{TEAM3_NAME} duration: {team3_result['duration']:.2f} seconds")
    
    # Updated return condition to check all three teams
    success = all([
        team1_result["success"], 
        team2_result["success"],
        team3_result["success"]
    ])
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 