#!/usr/bin/env python
"""
Utility to redistribute directories evenly across batch files.

This script takes a list of directories and distributes them
evenly across three batch files for team processing.
"""

import os
import argparse
import random
from pathlib import Path

# Default directories file
DEFAULT_DIRS_FILE = "directories_to_process.txt"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Redistribute directories across batch files")
    
    parser.add_argument(
        "--input-file", "-i",
        default=DEFAULT_DIRS_FILE,
        help=f"Input file containing all directories (default: {DEFAULT_DIRS_FILE})"
    )
    parser.add_argument(
        "--batch1", "-b1",
        default="batch1_directories.txt",
        help="Output file for Batch 1 (default: batch1_directories.txt)"
    )
    parser.add_argument(
        "--batch2", "-b2",
        default="batch2_directories.txt",
        help="Output file for Batch 2 (default: batch2_directories.txt)"
    )
    parser.add_argument(
        "--batch3", "-b3",
        default="batch3_directories.txt",
        help="Output file for Batch 3 (default: batch3_directories.txt)"
    )
    parser.add_argument(
        "--shuffle", "-s",
        action="store_true",
        help="Shuffle directories before distributing"
    )
    
    return parser.parse_args()

def load_directories(file_path):
    """Load directories from a file."""
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return []
    
    with open(file_path, "r") as f:
        # Read lines, strip whitespace, and filter out empty lines and comments
        directories = [
            line.strip() for line in f
            if line.strip() and not line.strip().startswith('#')
        ]
    
    return directories

def write_batch_file(file_path, team_name, directories):
    """Write directories to a batch file."""
    with open(file_path, "w") as f:
        f.write(f"# Batch Directories - {team_name}\n")
        f.write("# Lines starting with # are comments\n\n")
        
        for directory in directories:
            f.write(f"{directory}\n")
    
    print(f"Wrote {len(directories)} directories to {file_path}")

def main():
    """Main entry point."""
    args = parse_args()
    
    # Load directories
    directories = load_directories(args.input_file)
    
    if not directories:
        print("No directories found to redistribute")
        return 1
    
    print(f"Loaded {len(directories)} directories from {args.input_file}")
    
    # Shuffle if requested
    if args.shuffle:
        print("Shuffling directories")
        random.shuffle(directories)
    
    # Calculate split points for even distribution
    total = len(directories)
    chunk_size = total // 3
    remainder = total % 3
    
    # Distribute directories, handling any remainder
    batch1_dirs = directories[:chunk_size + (1 if remainder > 0 else 0)]
    batch2_dirs = directories[len(batch1_dirs):len(batch1_dirs) + chunk_size + (1 if remainder > 1 else 0)]
    batch3_dirs = directories[len(batch1_dirs) + len(batch2_dirs):]
    
    # Write batch files
    write_batch_file(args.batch1, "Team1", batch1_dirs)
    write_batch_file(args.batch2, "Team2", batch2_dirs)
    write_batch_file(args.batch3, "Team3", batch3_dirs)
    
    print("\nSummary:")
    print(f"Team1: {len(batch1_dirs)} directories")
    print(f"Team2: {len(batch2_dirs)} directories")
    print(f"Team3: {len(batch3_dirs)} directories")
    
    return 0

if __name__ == "__main__":
    exit(main()) 