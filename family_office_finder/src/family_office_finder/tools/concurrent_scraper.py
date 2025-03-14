#!/usr/bin/env python
"""
Script to concurrently scrape multiple websites using asyncio
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

async def scrape_url_task(scraper, url, max_depth=2, max_pages=10, max_time_minutes=5):
    """Task to scrape a single URL"""
    logger.info(f"Starting scrape task for: {url}")
    try:
        # Add https:// if the URL doesn't have a protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        result = await scraper.scrape_url(
            url=url,
            max_depth=max_depth,
            max_pages=max_pages,
            max_time_minutes=max_time_minutes
        )
        
        # Check if result is None before trying to access attributes
        if result is None:
            logger.warning(f"No result returned for {url}")
            return {
                "url": url,
                "success": False,
                "error": "No result returned from scraper"
            }
            
        # Make sure result is a dictionary before using .get()
        if isinstance(result, dict):
            return {
                "url": url,
                "success": True,
                "output_directory": result.get("output_directory", ""),
                "pages_crawled": result.get("pages_crawled", 0),
                "time_elapsed": result.get("time_elapsed", 0)
            }
        else:
            # Handle case where result is not None but also not a dictionary
            logger.warning(f"Result for {url} is not a dictionary: {type(result)}")
            return {
                "url": url,
                "success": True,
                "output_directory": str(result) if hasattr(result, "__str__") else "",
                "pages_crawled": 0,
                "time_elapsed": 0
            }
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

async def scrape_urls_concurrently(urls, max_depth=2, max_pages=10, max_time_minutes=5, max_concurrent=3):
    """Scrape multiple URLs concurrently using asyncio.gather"""
    logger.info(f"Starting concurrent scraping of {len(urls)} URLs with max_concurrent={max_concurrent}")
    
    # Create a single scraper instance
    scraper = PlaywrightScraper()
    
    # Process URLs in batches to limit concurrency
    results = []
    for i in range(0, len(urls), max_concurrent):
        batch = urls[i:i+max_concurrent]
        logger.info(f"Processing batch of {len(batch)} URLs ({i+1}-{i+len(batch)} of {len(urls)})")
        
        # Create tasks for each URL in the batch
        tasks = [
            scrape_url_task(
                scraper=scraper,
                url=url,
                max_depth=max_depth,
                max_pages=max_pages,
                max_time_minutes=max_time_minutes
            )
            for url in batch
        ]
        
        # Run tasks concurrently and collect results
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        logger.info(f"Completed batch of {len(batch)} URLs")
    
    # Save summary of all results
    summary_path = os.path.expanduser("~/Documents/Github/MA_Agents/family_office_finder/output/concurrent_scrape_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Concurrent scraping complete. Summary saved to {summary_path}")
    return results

async def read_urls_from_file_async(file_path):
    """Read URLs from a file asynchronously"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []
    
    # Use asyncio to read the file without blocking
    def _read_file():
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    # Run file reading in a thread pool to avoid blocking the event loop
    urls = await asyncio.to_thread(_read_file)
    
    logger.info(f"Found {len(urls)} URLs to scrape in {file_path}")
    return urls

async def scrape_urls_from_files_async(file_paths, max_depth=2, max_pages=10, max_time_minutes=5, max_concurrent=3):
    """Scrape URLs from multiple files concurrently"""
    # Read URLs from all files concurrently
    file_read_tasks = [read_urls_from_file_async(file_path) for file_path in file_paths]
    url_lists = await asyncio.gather(*file_read_tasks)
    
    # Create a scraper instance
    scraper = PlaywrightScraper()
    
    # Create tasks for each URL in each file, maintaining file grouping
    all_tasks = []
    for url_list in url_lists:
        file_tasks = [
            scrape_url_task(
                scraper=scraper,
                url=url,
                max_depth=max_depth,
                max_pages=max_pages,
                max_time_minutes=max_time_minutes
            )
            for url in url_list
        ]
        all_tasks.extend(file_tasks)
    
    # Run tasks with concurrency limit using semaphore
    sem = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(task):
        async with sem:
            return await task
    
    # Wrap each task with the semaphore
    limited_tasks = [run_with_semaphore(task) for task in all_tasks]
    
    # Run all tasks with concurrency control
    results = await asyncio.gather(*limited_tasks)
    
    # Save summary of all results
    summary_path = os.path.expanduser("~/Documents/Github/MA_Agents/family_office_finder/output/concurrent_scrape_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Concurrent scraping complete. Summary saved to {summary_path}")
    return results

def scrape_urls_from_file_concurrent(file_paths, max_depth=2, max_pages=10, max_time_minutes=5, max_concurrent=3):
    """Wrapper function to run the async scraping from synchronous code"""
    return asyncio.run(scrape_urls_from_files_async(
        file_paths=file_paths,
        max_depth=max_depth,
        max_pages=max_pages,
        max_time_minutes=max_time_minutes,
        max_concurrent=max_concurrent
    ))

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Concurrently scrape websites from a list of URLs')
    parser.add_argument('--files', '-f', nargs='+', help='One or more files containing URLs to scrape (one per line)')
    parser.add_argument('--urls', '-u', nargs='+', help='One or more URLs to scrape directly')
    parser.add_argument('--depth', '-d', type=int, default=2, help='Maximum link depth to follow (default: 2)')
    parser.add_argument('--pages', '-p', type=int, default=10, help='Maximum number of pages to crawl per site (default: 10)')
    parser.add_argument('--time', '-t', type=int, default=5, help='Maximum time in minutes to spend per site (default: 5)')
    parser.add_argument('--concurrent', '-c', type=int, default=3, help='Maximum number of concurrent scraping tasks (default: 3)')
    
    args = parser.parse_args()
    
    if not args.files and not args.urls:
        logger.error("Either --files or --urls must be specified")
        parser.print_help()
        sys.exit(1)
    
    if args.files:
        # Scrape URLs from files concurrently
        scrape_urls_from_file_concurrent(
            file_paths=args.files,
            max_depth=args.depth,
            max_pages=args.pages,
            max_time_minutes=args.time,
            max_concurrent=args.concurrent
        )
    else:
        # Scrape provided URLs concurrently
        asyncio.run(scrape_urls_concurrently(
            urls=args.urls,
            max_depth=args.depth,
            max_pages=args.pages,
            max_time_minutes=args.time,
            max_concurrent=args.concurrent
        ))

if __name__ == "__main__":
    main() 