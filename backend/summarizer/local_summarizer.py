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

# Import the summarizer and Claude
from backend.summarizer.summarizer import Summarizer
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LocalSummarizer(Summarizer):
    """Version of Summarizer that works with local files instead of S3."""
    
    def summarize_directory(self, directory_path: str) -> dict:
        """
        Extract and summarize key information from a local directory.
        
        Args:
            directory_path: The path to the local directory
            
        Returns:
            Dict containing summary data and metadata
        """
        logger.info(f"Summarizing content from local directory: {directory_path}")
        
        # Check if directory exists
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            logger.error(f"Local directory '{directory_path}' not found or is not a directory")
            return {
                "success": False,
                "error": f"Local directory '{directory_path}' not found or is not a directory",
                "directory": directory_path,
                "summary": {}
            }
        
        # Get all text files in the directory
        file_paths = list(Path(directory_path).glob("**/*.txt"))
        logger.info(f"Found {len(file_paths)} text files in directory '{directory_path}'")
        
        if not file_paths:
            logger.error(f"No text files found in directory '{directory_path}'")
            return {
                "success": False,
                "error": f"No text files found in directory '{directory_path}'",
                "directory": directory_path,
                "summary": {}
            }
        
        # Create a dictionary mapping file paths to their contents
        file_content_map = {}
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_content_map[str(file_path)] = content
                logger.info(f"Read content from file: {file_path.name}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
        
        if not file_content_map:
            logger.error(f"Failed to read content from any files in '{directory_path}'")
            return {
                "success": False,
                "error": f"Failed to read content from any files in '{directory_path}'",
                "directory": directory_path,
                "summary": {}
            }
        
        logger.info(f"Read content from {len(file_content_map)} files")
        
        # Extract portfolio companies
        logger.info("Extracting portfolio companies...")
        portfolio_companies = self._extract_portfolio_companies(file_content_map)
        
        # Create the summary result
        summary_result = {
            "success": True,
            "directory": directory_path,
            "file_count": len(file_content_map),
            "summary": {
                "portfolio_companies": portfolio_companies
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info(f"Summarization complete. Found {len(portfolio_companies)} portfolio companies.")
        return summary_result

def parse_args():
    parser = argparse.ArgumentParser(description="Summarize content from a local directory")
    parser.add_argument("--directory", "-d", required=True,
                        help="Local directory to analyze")
    
    # Change this line to use the local output directory
    current_dir = Path(__file__).resolve().parent
    default_output_dir = current_dir / "output"
    
    parser.add_argument("--output-dir", "-o", default=str(default_output_dir),
                        help="Output directory for the summary report")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Also save as JSON")
    
    return parser.parse_args()

def main():
    """Main entry point for the local directory summarizer tool."""
    parser = argparse.ArgumentParser(description="Summarize content from a local directory")
    parser.add_argument("--directory", "-d", default="/Users/lisun/Documents/branfordcastle.com",
                        help="Local directory to analyze (default: /Users/lisun/Documents/branfordcastle.com)")
    parser.add_argument("--output-dir", "-o", default=str(Path(__file__).resolve().parent.parent.parent / "output"),
                        help="Output directory for the summary report")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Also save as JSON")
    
    args = parser.parse_args()
    
    # Initialize the local summarizer
    summarizer = LocalSummarizer()
    
    try:
        # Extract and summarize the directory
        logger.info(f"Summarizing local directory: {args.directory}")
        summary_result = summarizer.summarize_directory(args.directory)
        
        # Generate the summary report
        report = summarizer.generate_summary_report(summary_result)
        
        # Create output directory if it doesn't exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = os.path.basename(args.directory)
        base_filename = f"{dir_name}_summary_{timestamp}"
        txt_filename = f"{base_filename}.txt"
        json_filename = f"{base_filename}.json"
        
        # Save the report to a text file
        txt_path = output_dir / txt_filename
        with open(txt_path, "w") as f:
            f.write(report)
        logger.info(f"Summary report saved to: {txt_path}")
        
        # Save JSON if requested
        if args.json:
            import json
            json_path = output_dir / json_filename
            with open(json_path, "w") as f:
                json.dump(summary_result, f, indent=2)
            logger.info(f"JSON data saved to: {json_path}")
        
        # Print the report to console
        print("\n" + "="*80)
        print(f"LOCAL DIRECTORY SUMMARY: {args.directory}")
        print("="*80)
        print(report)
        print("="*80)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 