import asyncio
import os
import json
import re
import datetime
import time
import logging
import argparse
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import aiohttp
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PlaywrightScraper:
    """Class for scraping websites with dynamic content using Playwright"""
    
    def __init__(self):
        """Initialize the scraper"""
        self.current_output_dir = ""
        self.robots_parsers = {}  # Cache for robots.txt parsers
        self.default_delay = 2  # Default delay in seconds if no robots.txt
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    
    async def get_robots_parser(self, url):
        """Get or create a robots.txt parser for the given URL"""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Return cached parser if available
        if base_url in self.robots_parsers:
            return self.robots_parsers[base_url]
        
        # Create a new parser
        parser = RobotFileParser()
        robots_url = f"{base_url}/robots.txt"
        parser.set_url(robots_url)
        
        try:
            # Fetch robots.txt content
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        # RobotFileParser expects to read from a file-like object
                        # So we'll create a list of lines
                        parser.parse(content.splitlines())
                        logger.info(f"Successfully fetched and parsed robots.txt from {robots_url}")
                    else:
                        logger.warning(f"Could not fetch robots.txt from {robots_url} (status: {response.status})")
                        parser = None
        except Exception as e:
            logger.warning(f"Error fetching robots.txt from {robots_url}: {e}")
            parser = None
        
        # Cache the parser
        self.robots_parsers[base_url] = parser
        return parser
    
    async def get_crawl_delay(self, url):
        """Get the crawl delay for the given URL from robots.txt"""
        parser = await self.get_robots_parser(url)
        
        if parser:
            delay = parser.crawl_delay("*")
            if delay:
                logger.info(f"Using crawl delay from robots.txt: {delay} seconds")
                return delay
            
        logger.info(f"No crawl delay specified in robots.txt, using default: {self.default_delay} seconds")
        return self.default_delay
    
    async def can_fetch(self, url, robots_parser):
        """Check if the URL can be fetched according to robots.txt"""
        if robots_parser:
            can_fetch = robots_parser.can_fetch(self.user_agent, url)
            if not can_fetch:
                logger.warning(f"URL {url} is disallowed by robots.txt")
            return can_fetch
        
        # If no robots.txt or error parsing, assume allowed
        return True
    
    def normalize_url(self, url):
        """Normalize URL to avoid crawling the same page with different URL formats"""
        parsed = urlparse(url)
        
        # Normalize the domain (remove or add www consistently)
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            # We'll standardize on the non-www version
            netloc = netloc[4:]
        
        # Normalize the path (remove trailing slash except for homepage)
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        
        # Rebuild the URL without query parameters and fragments
        normalized = f"{parsed.scheme}://{netloc}{path}"
        return normalized
    
    def create_output_directory(self, url):
        """Create an output directory for this run using the URL as the folder name"""
        # Create output directory in the same folder as this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_base = os.path.join(current_dir, "output")
        os.makedirs(output_base, exist_ok=True)
        
        # Create a clean URL-based directory name
        # Remove protocol (http:// or https://)
        folder_name = url.replace("https://", "").replace("http://", "").replace("www.", "")
        # Remove trailing slash if present
        if folder_name.endswith("/"):
            folder_name = folder_name[:-1]
        
        self.current_output_dir = os.path.join(output_base, folder_name)
        os.makedirs(self.current_output_dir, exist_ok=True)
        
        logger.info(f"Created output directory: {self.current_output_dir}")
        return self.current_output_dir
    
    def should_crawl_url(self, url):
        """Check if a URL should be crawled based on its file extension"""
        # Skip common non-HTML file types
        skip_extensions = [
            '.svg', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc', '.docx', 
            '.xls', '.xlsx', '.zip', '.tar', '.gz', '.mp3', '.mp4', '.avi',
            '.mov', '.wmv', '.css', '.js', '.xml', '.json', '.ico'
        ]
        
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        for ext in skip_extensions:
            if path.endswith(ext):
                logger.info(f"Skipping non-HTML file: {url}")
                return False
        
        return True

    async def scrape_url(self, url, max_depth=2, max_pages=10, max_time_minutes=5):
        """
        Generic crawler that handles any website with dynamic content.
    
        Args:
            url: Starting URL to crawl
            max_depth: Maximum link depth to follow (0 for unlimited)
            max_pages: Maximum number of pages to crawl (0 for unlimited)
            max_time_minutes: Maximum crawl time in minutes (0 for unlimited)
        """
        # Create output directory for this run
        output_dir = self.create_output_directory(url)
        
        # Set up time tracking
        start_time = time.time()
        max_time_seconds = max_time_minutes * 60 if max_time_minutes > 0 else float('inf')
        
        # Parse the base domain for staying within the same site
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        
        # Get robots.txt settings once at the beginning
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_parser = await self.get_robots_parser(base_url)
        crawl_delay = self.default_delay
        
        if robots_parser:
            delay = robots_parser.crawl_delay("*")
            if delay:
                crawl_delay = delay
                logger.info(f"Using crawl delay from robots.txt: {crawl_delay} seconds")
            else:
                logger.info(f"No crawl delay specified in robots.txt, using default: {crawl_delay} seconds")
        
        # Track visited URLs to avoid duplicates
        visited_urls = set()
        # Queue of URLs to visit with their depth
        url_queue = [(self.normalize_url(url), 0)]  # (normalized_url, depth)
        # Store page data
        all_pages_data = {}
        
        logger.info(f"Starting dynamic content crawler for {url}")
        logger.info(f"Depth limit: {'Unlimited' if max_depth <= 0 else max_depth}")
        logger.info(f"Page limit: {'Unlimited' if max_pages <= 0 else max_pages}")
        logger.info(f"Time limit: {'Unlimited' if max_time_minutes <= 0 else f'{max_time_minutes} minutes'}")
        logger.info(f"Crawl delay: {crawl_delay} seconds")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=self.user_agent
            )
            
            # Create a new page
            page = await context.new_page()
            
            # Process URLs until queue is empty or limits are reached
            pages_crawled = 0
            disallowed_urls = 0
            
            try:
                while url_queue:
                    # Check if we've reached the page limit
                    if max_pages > 0 and pages_crawled >= max_pages:
                        logger.info(f"Reached page limit of {max_pages}. Stopping crawl.")
                        break
                        
                    # Check if we've reached the time limit
                    elapsed_time = time.time() - start_time
                    if elapsed_time > max_time_seconds:
                        logger.info(f"Reached time limit of {max_time_minutes} minutes. Stopping crawl.")
                        break
                        
                    current_url, depth = url_queue.pop(0)  # BFS: take from beginning
                    normalized_url = self.normalize_url(current_url)
                    
                    if normalized_url in visited_urls:
                        continue
                        
                    # Check depth limit (only if max_depth > 0)
                    if max_depth > 0 and depth > max_depth:
                        continue
                    
                    # Skip non-HTML files
                    if not self.should_crawl_url(normalized_url):
                        visited_urls.add(normalized_url)  # Mark as visited so we don't try again
                        continue
                    
                    # Check robots.txt rules
                    if not await self.can_fetch(normalized_url, robots_parser):
                        logger.warning(f"Skipping {normalized_url} (disallowed by robots.txt)")
                        disallowed_urls += 1
                        continue
                    
                    visited_urls.add(normalized_url)
                    pages_crawled += 1
                    
                    # Print progress every 10 pages
                    if pages_crawled % 10 == 0:
                        elapsed_minutes = elapsed_time / 60
                        print(f"\nProgress update:")
                        print(f"- Pages crawled: {pages_crawled}")
                        print(f"- Queue size: {len(url_queue)}")
                        print(f"- Elapsed time: {elapsed_minutes:.1f} minutes")
                        print(f"- URLs disallowed by robots.txt: {disallowed_urls}")
                    
                    logger.info(f"[{pages_crawled}] Crawling: {normalized_url} (depth {depth})")
                    
                    # Navigate to the URL
                    try:
                        # First try with a more lenient wait strategy
                        try:
                            await page.goto(current_url, wait_until="domcontentloaded", timeout=15000)
                        except Exception as e:
                            logger.warning(f"Initial navigation to {current_url} with domcontentloaded timed out: {e}")
                            # If that fails, try with an even more basic strategy
                            await page.goto(current_url, wait_until="commit", timeout=10000)
                        
                        # Wait a bit for content to render, but don't wait for all network requests
                        try:
                            # Wait for common content indicators
                            await page.wait_for_selector('body', timeout=5000)
                            # Try to wait for main content if possible, but don't fail if not found
                            await page.wait_for_selector('main, #content, .content, article', timeout=5000, state='attached')
                        except Exception as content_error:
                            logger.info(f"Some content selectors not found, but continuing: {content_error}")
                        
                        # Add a small delay to allow some JS to execute
                        await asyncio.sleep(crawl_delay)
                    except Exception as e:
                        logger.error(f"Error navigating to {current_url}: {e}")
                        continue
                    
                    # Get page title
                    page_title = await page.title()
                    
                    # Create a data structure for this page
                    page_data = {
                        "url": current_url,
                        "title": page_title,
                        "base_content": "",
                        "dynamic_states": []
                    }

                    # Get the base content
                    base_content = await self.extract_page_content(page, current_url)
                    page_data["base_content"] = {"content": base_content}
                    print(f"  Extracted base content: {len(base_content)} chars")
                    
                    # Find and process interactive elements - pass the url_queue to collect new links
                    dynamic_links = await self.process_interactive_elements(
                        page, page_data, url_queue, visited_urls, base_domain, depth, crawl_delay
                    )
                    if dynamic_links:
                        print(f"  Found {len(dynamic_links)} new links in dynamic content")
                    
                    # Store the page data
                    all_pages_data[current_url] = page_data
                    
                    # Save individual page data
                    self.save_page_data(page_data, current_url)
                    
                    # If we haven't reached max depth or if depth is unlimited, find links to follow
                    if max_depth <= 0 or depth < max_depth:
                        # Find all links on the page (static content)
                        static_links = await self.extract_links_from_current_page(page)
                        new_static_links = self.process_new_links(static_links, url_queue, visited_urls, base_domain, depth)
                        
                        print(f"  Found {len(static_links)} links in static content, added {len(new_static_links)} new URLs to queue")
                        print(f"  Current queue size: {len(url_queue)} URLs")                    

                # Save all data to a single file
                # all_data_filename = os.path.join(output_dir, "all_pages_data.json")
                # with open(all_data_filename, "w") as f:
                #     json.dump(all_pages_data, f, indent=2)
                #     logger.info(f"Saved all data to {all_data_filename}")

                # print(f"\nCrawl complete! All data saved to {all_data_filename}")

                # Create a summary file
                summary_filename = os.path.join(output_dir, "crawl_summary.txt")
                with open(summary_filename, "w") as f:
                    elapsed_minutes = (time.time() - start_time) / 60
                    f.write(f"Crawl Summary for {url}\n")
                    f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Pages Crawled: {pages_crawled}\n")
                    f.write(f"Unique URLs: {len(visited_urls)}\n")
                    f.write(f"Time Taken: {elapsed_minutes:.2f} minutes\n\n")
                    
                    f.write("Crawled Pages:\n")
                    for i, page_url in enumerate(all_pages_data.keys()):
                        f.write(f"{i+1}. {page_url}\n")
                
                print(f"Crawl summary saved to {summary_filename}")
            
            except Exception as e:
                print(f"Error during crawling: {e}")
                import traceback
                traceback.print_exc()
        
            finally:
                # Close browser
                await browser.close()
        # Save a summary of all crawled pages
        with open(os.path.join(output_dir, "crawl_summary.txt"), "w") as f:
            summary = [{
                "url": url,
                "title": data["title"],
                "dynamic_states": len(data["dynamic_states"])
            } for url, data in all_pages_data.items()]
            json.dump(summary, f, indent=2)
            
    def scrape_url_sync(self, url, max_depth=2, max_pages=10, max_time_minutes=5):
        """Synchronous wrapper for scrape_url"""
        return asyncio.run(self.scrape_url(url, max_depth, max_pages, max_time_minutes))
    
    async def extract_page_content(self, page, url):
        """Extract the main content from a page"""
        try:
            content = await page.evaluate("""
                () => {
                    // Check if document.body exists
                    if (!document.body) {
                        return "[No text content available - this may be a non-HTML file]";
                    }
                    
                    // Try to find the main content area
                    const contentSelectors = [
                        'main', 'article', '[role="main"]', '#content', '.content', 
                        '.main-content', '.page-content', '.article-content'
                    ];
                    
                    for (const selector of contentSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.innerText && element.innerText.trim().length > 100) {
                            return element.innerText;
                        }
                    }
                    
                    // Fallback to body if no content container found
                    return document.body.innerText || "[No text content available]";
                }
            """)
            return content
        except Exception as e:
            logger.warning(f"Error extracting content from {url}: {e}")
            return "[Error extracting content]"
    
    async def extract_links_from_current_page(self, page):
        """Extract all links from the current page state"""
        links = await page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(href => href && !href.startsWith('javascript:') && !href.startsWith('#'));
            }
        """)
        return links
    
    def process_new_links(self, links, url_queue, visited_urls, base_domain, current_depth):
        """Process links and add new ones to the queue"""
        new_links = []
        
        # Normalize the base domain (remove www if present)
        if base_domain.startswith('www.'):
            base_domain = base_domain[4:]
        
        for link in links:
            normalized_link = self.normalize_url(link)
            parsed_link = urlparse(normalized_link)
            link_domain = parsed_link.netloc
            
            # Remove www from the link domain if present
            if link_domain.startswith('www.'):
                link_domain = link_domain[4:]
            
            # Compare domains without www
            if link_domain == base_domain and normalized_link not in visited_urls:
                # Check if this link is already in the queue
                if not any(normalized_link == url for url, _ in url_queue):
                    url_queue.append((normalized_link, current_depth + 1))
                    new_links.append(normalized_link)
        
        return new_links

    async def process_interactive_elements(self, page, page_data, url_queue, visited_urls, base_domain, current_depth, crawl_delay):
        """Find and interact with dynamic elements on the page and extract any new links"""
        new_links_found = []
        
        # 1. Process SELECT elements (dropdowns)
        select_elements = await page.evaluate("""
            () => {
                const selects = document.querySelectorAll('select');
                return Array.from(selects).map(select => {
                    return {
                        id: select.id || '',
                        name: select.name || '',
                        options: Array.from(select.options).map(option => ({
                            value: option.value,
                            text: option.text
                        })).filter(opt => opt.value)
                    };
                }).filter(select => select.options.length > 0);
            }
        """)
        
        if select_elements:
            print(f"  Found {len(select_elements)} select elements")
            
            for select_idx, select in enumerate(select_elements):
                print(f"  Processing select #{select_idx+1}: {select['name'] or select['id'] or 'unnamed'} with {len(select['options'])} options")
                
                # Create a selector for this dropdown
                select_selector = ""
                if select['id']:
                    select_selector = f"select#{select['id']}"
                elif select['name']:
                    select_selector = f"select[name='{select['name']}']"
                else:
                    select_selector = f"select:nth-of-type({select_idx+1})"
                
                # Process each option
                for option in select['options']:
                    if not option['value'] or option['value'] == "0" or option['value'].lower() == "select":
                        continue
                    
                    print(f"    Option: {option['text']} (value: {option['value']})")
                    
                    try:
                        # Select this option
                        await page.select_option(select_selector, option['value'])
                        await asyncio.sleep(crawl_delay)  # Use the passed crawl delay
                        
                        # Get the updated content
                        dynamic_content = await self.extract_page_content(page, option['value'])
                        
                        # Add to dynamic states
                        page_data["dynamic_states"].append({
                            "element_type": "select",
                            "element_info": {
                                "name": select['name'],
                                "id": select['id'],
                                "option_value": option['value'],
                                "option_text": option['text']
                            },
                            "content": dynamic_content
                        })
                        
                        print(f"    Captured content: {len(dynamic_content)} chars")
                        
                        # Extract links from this dynamic state
                        dynamic_links = await self.extract_links_from_current_page(page)
                        new_links = self.process_new_links(dynamic_links, url_queue, visited_urls, base_domain, current_depth)
                        new_links_found.extend(new_links)
                        if new_links:
                            print(f"    Found {len(new_links)} new links in this dynamic state")
                        
                    except Exception as e:
                        print(f"    Error selecting option: {e}")
        
        # Temporarily disable other sections until we find the problematic one
        """
        # 2. Process BUTTON elements
        # ... (comment out this section)
        
        # 3. Process TAB elements
        # ... (comment out this section)
        
        # 4. Process JavaScript-powered links
        # ... (comment out this section)
        
        # 5. Process accordions and collapsible elements
        # ... (comment out this section)
        
        # 6. Process custom dropdowns
        # ... (comment out this section)
        
        # 7. Process search inputs
        # ... (comment out this section)
        """
        
        return new_links_found    
    
    def save_page_data(self, page_data, url):
        """Save page data to files"""
        # Create a safe filename from the URL
        filename = urlparse(url).path
        if not filename or filename == "/":
            filename = "index"
        else:
            # Remove leading/trailing slashes and replace internal ones
            filename = filename.strip("/").replace("/", "_")
        
        # Remove any special characters
        filename = re.sub(r'[^a-zA-Z0-9_-]', '', filename)
        
        # Add a prefix if the filename is empty
        if not filename:
            filename = "page"
        
        # Save to a single file with all content
        # json_path = os.path.join(self.current_output_dir, f"{filename}.json")
        # with open(json_path, "w") as f:
        #     json.dump(page_data, f, indent=2)
        
        # logger.info(f"Saved complete page data to {json_path}")
        
        # Also save a text-only version for easy reading
        txt_path = os.path.join(self.current_output_dir, f"{filename}.txt")
        with open(txt_path, "w") as f:
            f.write(f"URL: {page_data['url']}\n")
            f.write(f"TITLE: {page_data['title']}\n\n")
            f.write("BASE CONTENT:\n")
            f.write("="*80 + "\n")
            f.write(page_data['base_content']['content'])
            f.write("\n\n")
            
            # Add dynamic states if available
            if page_data.get('dynamic_states'):
                f.write("DYNAMIC CONTENT:\n")
                f.write("="*80 + "\n")
                
                for i, state in enumerate(page_data['dynamic_states']):
                    element_type = state.get('element_type', 'unknown')
                    info = state.get('element_info', {})
                    
                    if element_type == 'button':
                        f.write(f"[{i+1}] BUTTON: {info.get('text', '')}\n")
                    elif element_type == 'tab':
                        f.write(f"[{i+1}] TAB: {info.get('text', '')}\n")
                    elif element_type == 'js_link':
                        f.write(f"[{i+1}] JS LINK: {info.get('text', '')}\n")
                    elif element_type == 'accordion':
                        f.write(f"[{i+1}] ACCORDION: {info.get('text', '')}\n")
                    elif element_type == 'custom_dropdown':
                        f.write(f"[{i+1}] CUSTOM DROPDOWN: {info.get('text', '')}\n")
                    elif element_type == 'search':
                        f.write(f"[{i+1}] SEARCH INPUT: {info.get('placeholder', '')}\n")
                    else:
                        f.write(f"[{i+1}] {element_type.upper()}\n")
                    
                    f.write("-"*80 + "\n")
                    f.write(state['content'])
                    f.write("\n\n")

# if __name__ == "__main__":
#     # Parse command line arguments
#     parser = argparse.ArgumentParser(description='Crawl a website with dynamic content handling')
#     parser.add_argument('url', help='URL to crawl (required)')
#     parser.add_argument('--depth', type=int, default=2,
#                         help='Maximum link depth to follow (default: %(default)s, use 0 for unlimited)')
#     parser.add_argument('--pages', type=int, default=10,
#                         help='Maximum number of pages to crawl (default: %(default)s, 0 for unlimited)')
#     parser.add_argument('--time-limit', type=int, default=5,
#                         help='Maximum crawl time in minutes (default: %(default)s, 0 for unlimited)')
    
#     args = parser.parse_args()
    
#     # Create an instance of the scraper and run it
#     scraper = PlaywrightScraper()
#     scraper.scrape_url_sync(
#         args.url,
#         max_depth=args.depth,
#         max_pages=args.pages,
#         max_time_minutes=args.time_limit
#     )

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Crawl a website with dynamic content handling')
    parser.add_argument('url', help='URL to crawl (required)')
    parser.add_argument('--depth', type=int, default=10,
                        help='Maximum link depth to follow (default: %(default)s, use 0 for unlimited)')
    parser.add_argument('--pages', type=int, default=0,
                        help='Maximum number of pages to crawl (default: %(default)s, 0 for unlimited)')
    parser.add_argument('--time-limit', type=int, default=0,
                        help='Maximum crawl time in minutes (default: %(default)s, 0 for unlimited)')
    
    args = parser.parse_args()
    
    # Create an instance of the scraper
    scraper = PlaywrightScraper()

    # Run the crawler with parameters from command line
    asyncio.run(scraper.scrape_url(
        args.url,
        max_depth=args.depth,
        max_pages=args.pages,
        max_time_minutes=args.time_limit
    ))
    