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
from backend.scraper_agent.src.scraper.tools.playwright_scraper import PlaywrightScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def scrape_url_batch(urls, max_depth=2, max_pages=10, max_time_minutes=5):
    """Scrape a batch of URLs using a single PlaywrightScraper instance"""
    logger.info(f"Starting batch with {len(urls)} URLs")
    
    # Create a scraper instance for this batch
    scraper = PlaywrightScraper()
    
    # Process each URL in the batch
    results = []
    for i, url in enumerate(urls):
        logger.info(f"Scraping URL {i+1}/{len(urls)} in batch: {url}")
        try:
            result = await scraper.scrape_url(
                url=url,
                max_depth=max_depth,
                max_pages=max_pages,
                max_time_minutes=max_time_minutes
            )
            
            # Check if result is None before trying to use .get()
            if result is None:
                logger.warning(f"No result returned for {url}")
                results.append({
                    "url": url,
                    "success": False,
                    "error": "No result returned from scraper"
                })
            else:
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
    
    logger.info(f"Completed batch of {len(urls)} URLs")
    return results

async def scrape_urls_from_file_concurrent(file_path, batch_size=5, max_depth=2, max_pages=10, max_time_minutes=5):
    """Scrape URLs from a file concurrently in batches"""
    # Read URLs from file
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    logger.info(f"Found {len(urls)} URLs to scrape in {file_path}")
    
    # Split URLs into batches
    batches = [urls[i:i+batch_size] for i in range(0, len(urls), batch_size)]
    logger.info(f"Split into {len(batches)} batches of up to {batch_size} URLs each")
    
    # Create tasks for each batch
    tasks = [
        scrape_url_batch(
            urls=batch,
            max_depth=max_depth,
            max_pages=max_pages,
            max_time_minutes=max_time_minutes
        )
        for batch in batches
    ]
    
    # Run all batches concurrently
    batch_results = await asyncio.gather(*tasks)
    
    # Flatten results
    results = [result for batch in batch_results for result in batch]
    
    # Save summary of all results
    summary_path = os.path.expanduser("~/Documents/Github/MA_Agents/scraper_agent/output/scrape_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Scraping complete. Summary saved to {summary_path}")
    return results

def scrape_urls_from_file(file_path, batch_size=5, max_depth=2, max_pages=10, max_time_minutes=5):
    """Wrapper function to run the async scraping from synchronous code"""
    return asyncio.run(scrape_urls_from_file_concurrent(
        file_path=file_path,
        batch_size=batch_size,
        max_depth=max_depth,
        max_pages=max_pages,
        max_time_minutes=max_time_minutes
    ))

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
    parser.add_argument('--depth', '-d', type=int, default=10, help='Maximum link depth to follow (default: 10)')
    parser.add_argument('--pages', '-p', type=int, default=0, help='Maximum number of pages to crawl per site (default: 0)')
    parser.add_argument('--time', '-t', type=int, default=10, help='Maximum time in minutes to spend per site (default: 10)')
    parser.add_argument('--batch-size', '-b', type=int, default=5, help='Number of URLs to process per batch (default: 5)')
    
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
            batch_size=args.batch_size,
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