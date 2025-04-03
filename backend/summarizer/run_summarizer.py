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
        # Extract and summarize the directory using only LLM-based extraction
        logger.info(f"Summarizing directory: {args.directory}")
        summary_result = summarizer.summarize_directory(args.directory)
        
        # Get the firm name
        firm_name = summary_result.get("firm_name", args.directory.split('.')[0].capitalize())
        logger.info(f"Analyzing portfolio companies for: {firm_name}")
        
        # Verify portfolio companies - perform a sanity check
        portfolio_companies = summary_result['summary']['portfolio_companies']
        
        # Count different types of companies
        portfolio_count = sum(1 for company in portfolio_companies if company.get('from_portfolio_file', False))
        affiliate_count = sum(1 for company in portfolio_companies if company.get('affiliate', False))
        domain_count = sum(1 for company in portfolio_companies if '.com' in company.get('name', '').lower() or '.net' in company.get('name', '').lower())
        
        logger.info(f"Final portfolio file companies count: {portfolio_count}")
        logger.info(f"Including affiliate transactions: {affiliate_count}")
        
        # Warning if we still have companies that look like domains
        if domain_count > 0:
            logger.warning(f"Found {domain_count} companies with domain-like names. Should be 0.")
        
        # Additional check: if portfolio count is too low, print a warning
        if portfolio_count < 15 and any(f.lower().endswith('portfolio.txt') for f in summarizer.s3_client.list_files_by_directory().get(args.directory, [])):
            logger.warning(f"WARNING: Only {portfolio_count} companies from portfolio.txt were included in the final results.")
            logger.warning("This may indicate an issue with extraction or deduplication.")
        
        # Generate the summary report
        report = summarizer.generate_summary_report(summary_result)
        
        # Generate filenames based on directory name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_dir_name = args.directory.replace(".", "_").replace("/", "_")
        safe_firm_name = firm_name.replace(" ", "_").lower()
        txt_filename = f"{safe_dir_name}_{safe_firm_name}_summary_{timestamp}.txt"
        json_filename = f"{safe_dir_name}_{safe_firm_name}_summary_{timestamp}.json"
        
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
            
        # Generate deduplication report
        if hasattr(summarizer, 'all_extracted_companies'):
            dedup_path = summarizer._save_deduplication_report(args.directory, output_dir)
            if dedup_path:
                logger.info(f"Deduplication report saved to: {dedup_path}")
                print(f"Deduplication report saved to: {dedup_path}")
            else:
                logger.warning("Could not generate deduplication report")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 