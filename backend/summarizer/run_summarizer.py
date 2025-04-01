import os
import sys
import logging
from pathlib import Path
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Set default output directory to the summarizer/output folder
default_output_dir = current_dir / "output"

# Import the Summarizer
from backend.summarizer.summarizer import Summarizer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="Summarize content from an S3 directory")
    parser.add_argument("--directory", "-d", default="branfordcastle.com", 
                        help="S3 directory to analyze (default: branfordcastle.com)")
    parser.add_argument("--output-dir", "-o", default=str(default_output_dir),
                        help="Output directory for the summary report")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Also save as JSON")
    
    return parser.parse_args()

def main():
    """Main entry point for the directory summarizer tool."""
    # Parse command line arguments
    args = parse_args()
    
    # Initialize the summarizer
    summarizer = Summarizer()
    
    # Create absolute path for output directory - fix for nested path issues
    if not os.path.isabs(args.output_dir):
        # If relative path, make it relative to current directory
        output_dir = os.path.abspath(os.path.join(current_dir, args.output_dir))
    else:
        output_dir = args.output_dir
    
    # If the path contains "backend/reasoning_agent/output", switch to using local output folder
    if "backend/reasoning_agent/output" in output_dir:
        output_dir = str(default_output_dir)
        logger.info(f"Redirecting output to local folder: {output_dir}")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Using output directory: {output_dir}")
    
    try:
        # Extract and summarize the directory
        logger.info(f"Summarizing directory: {args.directory}")
        summary_result = summarizer.summarize_directory(args.directory)
        
        # Generate the summary report
        report = summarizer.generate_summary_report(summary_result)
        
        # Generate filenames based on directory name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_dir_name = args.directory.replace(".", "_").replace("/", "_")
        txt_filename = f"{safe_dir_name}_summary_{timestamp}.txt"
        json_filename = f"{safe_dir_name}_summary_{timestamp}.json"
        
        # Create full file paths
        txt_path = os.path.join(output_dir, txt_filename)
        
        # Write report to file
        with open(txt_path, "w") as f:
            f.write(report)
        
        logger.info(f"Summary report saved to: {txt_path}")
        print(f"\nSummary report saved to: {txt_path}")
        
        # Save JSON if requested
        if args.json:
            import json
            json_path = os.path.join(output_dir, json_filename)
            with open(json_path, "w") as f:
                json.dump(summary_result, f, indent=2)
            logger.info(f"JSON data saved to: {json_path}")
            print(f"JSON data saved to: {json_path}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 