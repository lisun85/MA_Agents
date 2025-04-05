#!/usr/bin/env python
"""
Multi-directory runner for the Summarizer.

This script allows running the summarizer on multiple directories concurrently.
"""

import os
import sys
import argparse
import logging
import concurrent.futures
import subprocess
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_directory_summarizer.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_DIRS_FILE = "directories_to_process.txt"
MAX_WORKERS = 3  # Number of directories to process in parallel

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run summarizer on multiple directories")
    
    # Input options - either a file or comma-separated list
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "--dirs-file", "-f", 
        help=f"File containing directories to process (one per line, default: {DEFAULT_DIRS_FILE})",
        default=DEFAULT_DIRS_FILE
    )
    input_group.add_argument(
        "--dirs", "-d", 
        help="Comma-separated list of directories to process"
    )
    
    # Other options
    parser.add_argument(
        "--parallel", "-p", 
        action="store_true",
        help="Use parallel extraction for faster processing within each directory"
    )
    parser.add_argument(
        "--output-dir", "-o", 
        help="Output directory for summaries"
    )
    parser.add_argument(
        "--max-workers", "-m", 
        type=int, 
        default=MAX_WORKERS,
        help=f"Maximum number of directories to process in parallel (default: {MAX_WORKERS})"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    
    return parser.parse_args()

def load_directories_from_file(file_path: str) -> List[str]:
    """
    Load directories from a file (one per line).
    
    Args:
        file_path: Path to the file containing directories
        
    Returns:
        List of directory names
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []
    
    with open(file_path, 'r') as f:
        # Read lines, strip whitespace, and filter out empty lines and comments
        directories = [
            line.strip() for line in f
            if line.strip() and not line.strip().startswith('#')
        ]
    
    return directories

def process_directory(directory: str, use_parallel: bool, output_dir: Optional[str], debug: bool) -> bool:
    """
    Process a single directory using the summarizer.
    
    Args:
        directory: Name of the directory to process
        use_parallel: Whether to use parallel extraction
        output_dir: Output directory for the summary report
        debug: Whether to enable debug mode
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Processing directory: {directory}")
    
    # Get the path to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    summarizer_script = os.path.join(script_dir, "run_summarizer.py")
    
    # Construct the command with full path
    cmd = ["python", summarizer_script, "--directory", directory]
    
    if use_parallel:
        cmd.append("--parallel")
    
    if output_dir:
        cmd.extend(["--output-dir", output_dir])
    
    if debug:
        cmd.append("--debug")
    
    # Run the command
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info(f"Successfully processed {directory}")
            return True
        else:
            logger.error(f"Error processing {directory}: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Exception processing {directory}: {str(e)}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Get directories to process
    if args.dirs:
        directories = [d.strip() for d in args.dirs.split(',') if d.strip()]
    else:
        # Default to file if no --dirs provided
        file_path = args.dirs_file
        
        # Try to find the file relative to the script directory if not found
        if not os.path.exists(file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, args.dirs_file)
        
        directories = load_directories_from_file(file_path)
    
    if not directories:
        logger.error("No directories specified to process")
        return 1
    
    logger.info(f"Processing {len(directories)} directories: {', '.join(directories)}")
    
    # Create output directory if specified
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        logger.info(f"Output directory: {args.output_dir}")
    
    # Process directories in parallel
    success_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit tasks
        future_to_dir = {
            executor.submit(
                process_directory, 
                directory, 
                args.parallel, 
                args.output_dir, 
                args.debug
            ): directory for directory in directories
        }
        
        # Process results
        for future in concurrent.futures.as_completed(future_to_dir):
            directory = future_to_dir[future]
            try:
                success = future.result()
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error processing {directory}: {str(e)}")
    
    # Report results
    logger.info(f"Completed processing {len(directories)} directories")
    logger.info(f"Successful: {success_count}, Failed: {len(directories) - success_count}")
    
    return 0 if success_count == len(directories) else 1

if __name__ == "__main__":
    sys.exit(main()) 