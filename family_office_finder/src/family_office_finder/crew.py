import os
import logging
from typing import Dict, List, Any
from crewai import Crew, Agent, Task, Process
from crewai.tasks.task_output import TaskOutput
from crewai.tools import tool  # Use CrewAI's tool decorator instead
from family_office_finder.tools.playwright_scraper import PlaywrightScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FamilyOfficeFinderCrew:
    """Crew for finding and analyzing family offices"""
    
    def __init__(self):
        """Initialize the crew with necessary tools and components"""
        self.scraper = PlaywrightScraper()
    
    @tool("scrape_website")
    def scrape_website(self, url: str, max_depth: int = 2, max_pages: int = 10, max_time_minutes: int = 5) -> str:
        """
        Scrape a website using Playwright to extract content and follow links
        
        Args:
            url: The URL to scrape
            max_depth: Maximum link depth to follow (default: 2)
            max_pages: Maximum number of pages to crawl (default: 10)
            max_time_minutes: Maximum time in minutes to spend (default: 5)
            
        Returns:
            A summary of the scraping results
        """
        try:
            result = self.scraper.scrape_url_sync(
                url=url,
                max_depth=max_depth,
                max_pages=max_pages,
                max_time_minutes=max_time_minutes
            )
            return f"Successfully scraped {url}. Output directory: {result.get('output_directory', '')}, Pages crawled: {result.get('pages_crawled', 0)}"
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return f"Error scraping {url}: {str(e)}"
    
    def web_scraper_agent(self) -> Agent:
        """Create a web scraper agent"""
        return Agent(
            role="Web Scraper",
            goal="Scrape websites thoroughly to extract all relevant information",
            backstory="I am an expert web scraper that can navigate complex websites, handle dynamic content, and extract structured data.",
            tools=[self.scrape_website],
            verbose=True
        )
    
    def scrape_urls_task(self) -> Task:
        """Create a task to scrape URLs from a file"""
        return Task(
            description="Scrape all websites listed in the urls_to_scrape.txt file",
            expected_output="A summary of all scraped websites with their content saved to the output directory",
            agent=self.web_scraper_agent()
        )
    
    def run(self, urls_file: str = "urls_to_scrape.txt") -> TaskOutput:
        """Run the crew to scrape websites from a file"""
        # Read URLs from file
        if not os.path.exists(urls_file):
            logger.error(f"File not found: {urls_file}")
            return TaskOutput(
                task_id="scrape_websites",
                output=f"Error: {urls_file} file not found",
                success=False
            )
        
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        if not urls:
            logger.error(f"No URLs found in {urls_file}")
            return TaskOutput(
                task_id="scrape_websites",
                output=f"Error: No URLs found in {urls_file}",
                success=False
            )
        
        logger.info(f"Found {len(urls)} URLs to scrape in {urls_file}")
        
        # Create the crew
        crew = Crew(
            agents=[self.web_scraper_agent()],
            tasks=[self.scrape_urls_task()],
            verbose=True,
            process=Process.sequential
        )
        
        # Run the crew
        result = crew.kickoff(
            inputs={
                "urls": urls
            }
        )
        
        return result
