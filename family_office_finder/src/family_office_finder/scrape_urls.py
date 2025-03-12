#!/usr/bin/env python
"""
Script to scrape websites from a list of URLs
"""

import os
import sys
import json
import argparse
import logging
import asyncio
from dotenv import load_dotenv
from family_office_finder.tools.playwright_scraper import PlaywrightScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def scrape_urls_from_file(file_path, max_depth=2, max_pages=10, max_time_minutes=5):
    """Scrape URLs from a file"""
    # Read URLs from file
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    logger.info(f"Found {len(urls)} URLs to scrape in {file_path}")
    
    # Create scraper
    scraper = PlaywrightScraper()
    
    # Scrape each URL
    results = []
    for i, url in enumerate(urls):
        logger.info(f"Scraping URL {i+1}/{len(urls)}: {url}")
        try:
            result = scraper.scrape_url_sync(
                url=url,
                max_depth=max_depth,
                max_pages=max_pages,
                max_time_minutes=max_time_minutes
            )
            results.append({
                "url": url,
                "success": True,
                "output_directory": result.get("output_directory", ""),
                "pages_crawled": result.get("pages_crawled", 0)
            })
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            results.append({
                "url": url,
                "success": False,
                "error": str(e)
            })
    
    # Save summary of all results
    summary_path = os.path.expanduser("~/Documents/Github/MA_Agents/family_office_finder/output/scrape_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Scraping complete. Summary saved to {summary_path}")
    return results

async def scrape_single_url(url, max_depth=2, max_pages=10, max_time_minutes=5):
    """Scrape a single URL asynchronously"""
    logger.info(f"Scraping URL: {url}")
    
    # Create scraper
    scraper = PlaywrightScraper()
    
    # Scrape the URL
    try:
        result = await scraper.scrape_url(
            url=url,
            max_depth=max_depth,
            max_pages=max_pages,
            max_time_minutes=max_time_minutes
        )
        return {
            "url": url,
            "success": True,
            "output_directory": result.get("output_directory", ""),
            "pages_crawled": result.get("pages_crawled", 0)
        }
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Scrape websites from a list of URLs')
    parser.add_argument('--file', '-f', help='Path to file containing URLs to scrape (one per line)')
    parser.add_argument('--url', '-u', help='Single URL to scrape')
    parser.add_argument('--depth', '-d', type=int, default=2, help='Maximum link depth to follow (default: 2)')
    parser.add_argument('--pages', '-p', type=int, default=10, help='Maximum number of pages to crawl per site (default: 10)')
    parser.add_argument('--time', '-t', type=int, default=5, help='Maximum time in minutes to spend per site (default: 5)')
    
    args = parser.parse_args()
    
    if not args.file and not args.url:
        logger.error("Either --file or --url must be specified")
        parser.print_help()
        sys.exit(1)
    
    if args.file:
        # Check if file exists
        if not os.path.exists(args.file):
            logger.error(f"File not found: {args.file}")
            sys.exit(1)
        
        # Scrape URLs from file
        scrape_urls_from_file(
            file_path=args.file,
            max_depth=args.depth,
            max_pages=args.pages,
            max_time_minutes=args.time
        )
    else:
        # Scrape single URL
        result = asyncio.run(scrape_single_url(
            url=args.url,
            max_depth=args.depth,
            max_pages=args.pages,
            max_time_minutes=args.time
        ))
        
        # Print result
        if result["success"]:
            logger.info(f"Successfully scraped {args.url}")
            logger.info(f"Output directory: {result['output_directory']}")
            logger.info(f"Pages crawled: {result['pages_crawled']}")
        else:
            logger.error(f"Failed to scrape {args.url}: {result['error']}")

if __name__ == "__main__":
    main() 