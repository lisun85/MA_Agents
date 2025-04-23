"""
Email Agent Entry Point.

This script is the main entry point for running the email agent.
"""

import os
import sys
import logging
import argparse
from backend.email_agent.email_agent import EmailAgent
from backend.email_agent.config import OUTPUT_DIR, EMAIL_TEMPLATE_PATH
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate personalized emails for strong buyers")
    
    parser.add_argument(
        "--output-dir",
        help=f"Output directory for email documents (default: {OUTPUT_DIR})"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    
    parser.add_argument(
        "--single-file",
        help="Process only a single specified file"
    )
    
    parser.add_argument(
        "--template",
        help="Path to the email template image"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the email agent."""
    args = parse_args()
    
    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Create custom output directory if specified
    output_dir = OUTPUT_DIR
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use custom template path if specified
    template_path = EMAIL_TEMPLATE_PATH
    if args.template:
        template_path = Path(args.template)
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return 1
    
    logger.info("Starting email generation process...")
    
    # Create and run the email agent
    agent = EmailAgent(template_path=template_path, output_dir=output_dir)
    
    # Run with single file if specified
    if args.single_file:
        result = agent.run(single_file=args.single_file)
    else:
        result = agent.run()
    
    # Print summary
    logger.info(f"Email generation completed:")
    logger.info(f"  Total files: {result['stats']['total']}")
    logger.info(f"  Successfully processed: {result['stats']['successful']}")
    logger.info(f"  Failed: {result['stats']['failed']}")
    
    if 'summary_file' in result:
        logger.info(f"Summary saved to: {result['summary_file']}")
    
    return 0 if result['stats']['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 