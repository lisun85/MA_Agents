import asyncio
import os
import json
import re
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import argparse
import time

load_dotenv()

# Add this function to normalize URLs
def normalize_url(url):
    """Normalize URL to avoid crawling the same page with different URL formats"""
    parsed = urlparse(url)
    # Normalize the path (remove trailing slash except for homepage)
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    
    # Rebuild the URL without query parameters and fragments
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    return normalized

async def crawl_dynamic_website(url, max_depth=10, max_pages=0, max_time_minutes=0):
    """
    Generic crawler that handles any website with dynamic content.
    
    Args:
        url: Starting URL to crawl
        max_depth: Maximum link depth to follow (0 for unlimited)
        max_pages: Maximum number of pages to crawl (0 for unlimited)
        max_time_minutes: Maximum crawl time in minutes (0 for unlimited)
    """
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Set up time tracking
    start_time = time.time()
    max_time_seconds = max_time_minutes * 60 if max_time_minutes > 0 else float('inf')
    
    # Parse the base domain for staying within the same site
    parsed_url = urlparse(url)
    base_domain = parsed_url.netloc
    
    # Track visited URLs to avoid duplicates
    visited_urls = set()
    # Queue of URLs to visit with their depth
    url_queue = [(normalize_url(url), 0)]  # (normalized_url, depth)
    # Store page data
    all_pages_data = {}
    
    print(f"Starting generic dynamic content crawler for {url}")
    print(f"Depth limit: {'Unlimited' if max_depth <= 0 else max_depth}")
    print(f"Page limit: {'Unlimited' if max_pages <= 0 else max_pages}")
    print(f"Time limit: {'Unlimited' if max_time_minutes <= 0 else f'{max_time_minutes} minutes'}")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        )
        
        # Create a new page
        page = await context.new_page()
        
        # Process URLs until queue is empty or limits are reached
        pages_crawled = 0
        
        try:
            while url_queue:
                # Check if we've reached the page limit
                if max_pages > 0 and pages_crawled >= max_pages:
                    print(f"\nReached page limit of {max_pages}. Stopping crawl.")
                    break
                    
                # Check if we've reached the time limit
                elapsed_time = time.time() - start_time
                if elapsed_time > max_time_seconds:
                    print(f"\nReached time limit of {max_time_minutes} minutes. Stopping crawl.")
                    break
                    
                current_url, depth = url_queue.pop(0)  # BFS: take from beginning
                normalized_url = normalize_url(current_url)
                
                if normalized_url in visited_urls:
                    continue
                    
                # Check depth limit (only if max_depth > 0)
                if max_depth > 0 and depth > max_depth:
                    continue
                
                visited_urls.add(normalized_url)
                pages_crawled += 1
                
                # Print progress every 10 pages
                if pages_crawled % 10 == 0:
                    elapsed_minutes = elapsed_time / 60
                    print(f"\nProgress update:")
                    print(f"- Pages crawled: {pages_crawled}")
                    print(f"- Unique URLs found: {len(visited_urls)}")
                    print(f"- Queue size: {len(url_queue)}")
                    print(f"- Elapsed time: {elapsed_minutes:.1f} minutes")
                
                print(f"\n[{pages_crawled}] Crawling: {current_url} (Depth: {depth})")
                
                # Navigate to the URL
                try:
                    await page.goto(current_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(2)  # Wait for any delayed JS
                except Exception as e:
                    print(f"  Error navigating to {current_url}: {e}")
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
                base_content = await extract_page_content(page)
                page_data["base_content"] = base_content
                print(f"  Extracted base content: {len(base_content)} chars")
                
                # Find and process interactive elements - pass the url_queue to collect new links
                dynamic_links = await process_interactive_elements(page, page_data, url_queue, visited_urls, base_domain, depth)
                if dynamic_links:
                    print(f"  Found {len(dynamic_links)} new links in dynamic content")
                
                # Store the page data
                all_pages_data[current_url] = page_data
                
                # Save individual page data
                save_page_data(current_url, page_data)
                
                # If we haven't reached max depth or if depth is unlimited, find links to follow
                if max_depth <= 0 or depth < max_depth:
                    # Find all links on the page (static content)
                    static_links = await extract_links_from_current_page(page)
                    new_static_links = process_new_links(static_links, url_queue, visited_urls, base_domain, depth)
                    
                    print(f"  Found {len(static_links)} links in static content, added {len(new_static_links)} new URLs to queue")
                    print(f"  Current queue size: {len(url_queue)} URLs")
            
            # Calculate final statistics
            elapsed_time = time.time() - start_time
            elapsed_minutes = elapsed_time / 60
            
            print(f"\nCrawl complete!")
            print(f"- Total pages crawled: {pages_crawled}")
            print(f"- Total unique URLs found: {len(visited_urls)}")
            print(f"- Total time: {elapsed_minutes:.1f} minutes")
            print(f"Results saved to output/ directory")
            
        except Exception as e:
            print(f"Error during crawling: {e}")
        
        finally:
            # Close browser
            await browser.close()
    
    # Save a summary of all crawled pages
    with open("output/crawl_summary.json", "w") as f:
        summary = [{
            "url": url,
            "title": data["title"],
            "dynamic_states": len(data["dynamic_states"])
        } for url, data in all_pages_data.items()]
        json.dump(summary, f, indent=2)

async def extract_page_content(page):
    """Extract the main content from a page"""
    content = await page.evaluate("""
        () => {
            // Try to find the main content area
            const contentSelectors = [
                'main', 'article', '[role="main"]', '#content', '.content', 
                '.main-content', '.page-content', '.article-content'
            ];
            
            for (const selector of contentSelectors) {
                const element = document.querySelector(selector);
                if (element && element.innerText.trim().length > 100) {
                    return element.innerText;
                }
            }
            
            // Fallback to body if no content container found
            return document.body.innerText;
        }
    """)
    return content

async def extract_links_from_current_page(page):
    """Extract all links from the current page state"""
    links = await page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(href => href && !href.startsWith('javascript:') && !href.startsWith('#'));
        }
    """)
    return links

def process_new_links(links, url_queue, visited_urls, base_domain, current_depth):
    """Process links and add new ones to the queue"""
    new_links = []
    for link in links:
        normalized_link = normalize_url(link)
        if urlparse(normalized_link).netloc == base_domain and normalized_link not in visited_urls:
            # Check if this link is already in the queue
            if not any(normalized_link == url for url, _ in url_queue):
                url_queue.append((normalized_link, current_depth + 1))
                new_links.append(normalized_link)
    return new_links

async def process_interactive_elements(page, page_data, url_queue, visited_urls, base_domain, current_depth):
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
                    await asyncio.sleep(2)  # Wait for content to update
                    
                    # Get the updated content
                    dynamic_content = await extract_page_content(page)
                    
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
                    dynamic_links = await extract_links_from_current_page(page)
                    new_links = process_new_links(dynamic_links, url_queue, visited_urls, base_domain, current_depth)
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

def save_page_data(url, page_data):
    """Save all data for a page to a single file"""
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
    with open(f"output/{filename}.json", "w") as f:
        json.dump(page_data, f, indent=2)
    
    print(f"  Saved complete page data to output/{filename}.json")
    
    # Also save a text-only version for easy reading
    with open(f"output/{filename}.txt", "w") as f:
        f.write(f"URL: {page_data['url']}\n")
        f.write(f"TITLE: {page_data['title']}\n\n")
        f.write("BASE CONTENT:\n")
        f.write("="*80 + "\n")
        f.write(page_data['base_content'])
        f.write("\n\n")
        
        if page_data['dynamic_states']:
            f.write("DYNAMIC STATES:\n")
            f.write("="*80 + "\n")
            
            for i, state in enumerate(page_data['dynamic_states']):
                element_type = state['element_type']
                info = state['element_info']
                
                if element_type == 'select':
                    f.write(f"[{i+1}] SELECT: {info.get('name', '')} - Option: {info.get('option_text', '')}\n")
                elif element_type == 'button':
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
    
    # Run the crawler with parameters from command line
    asyncio.run(crawl_dynamic_website(
        args.url,
        max_depth=args.depth,
        max_pages=args.pages,
        max_time_minutes=args.time_limit
    ))