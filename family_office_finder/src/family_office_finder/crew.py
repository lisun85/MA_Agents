import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import EXASearchTool, FirecrawlScrapeWebsiteTool, SerperDevTool
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


@CrewBase
class FamilyOfficeFinderCrew():
   """Crew for discovering family office investors in Chicago"""


   @agent
   def family_office_discovery_agent(self) -> Agent:
       """Creates the Family Office Discovery Agent"""
       # Get the EXA API key from environment variables
       exa_api_key = os.environ.get("EXA_API_KEY")
      
       # Ensure the API key is available
       if not exa_api_key:
           raise ValueError("EXA_API_KEY environment variable is not set")
      
       #Create an instance of the EXA search tool
       exa_search_tool = EXASearchTool(api_key=exa_api_key)


       return Agent(
           config=self.agents_config['family_office_discovery_agent'],
           verbose=True,
           tools=[exa_search_tool],  # Pass the API key directly
           llm="gpt-4o-mini",  # Using a capable model for complex research
           max_iter=30
       )
   
   @agent
   def family_office_profile_agent(self) -> Agent:
    """Creates the Family Office Profile Agent with direct URL targeting"""
    # Get the Firecrawl API key from environment variables
    firecrawl_api_key = os.environ.get("FIRECRAWL_API_KEY")
    
    # Ensure the API key is available
    if not firecrawl_api_key:
        raise ValueError("FIRECRAWL_API_KEY environment variable is not set")
    
    # Create the FirecrawlScrapeWebsiteTool with improved configuration
    scrape_tool = FirecrawlScrapeWebsiteTool(
        api_key=firecrawl_api_key,
        # Include additional parameters for better contact info extraction
        params={
            'formats': ['markdown', 'html'],  # Get both formats for better parsing
            'include_links': True,            # Include links for navigation
            'include_images': False,          # Skip images to focus on text
            'include_contact_info': True,     # Explicitly request contact info
            'max_pages': 1,                   # Focus on one page at a time for better control
            'follow_links': False,            # We'll manually handle specific pages
        }
    )
    
    return Agent(
        config=self.agents_config['family_office_profile_agent'],
        verbose=True,
        tools=[scrape_tool],
        llm="gpt-4o-mini",  # Using a capable model for detailed extraction
        max_iter=60  # Increased to allow for more processing time
    )
   
   @agent
   def family_office_news_agent(self) -> Agent:
       """Creates the Family Office News Agent"""
       # Get the Serper API key from environment variables
       serper_api_key = os.environ.get("SERPER_API_KEY")
       
       # Ensure the API key is available
       if not serper_api_key:
           raise ValueError("SERPER_API_KEY environment variable is not set")
       
       return Agent(
           config=self.agents_config['family_office_news_agent'],
           verbose=True,
           tools=[SerperDevTool(api_key=serper_api_key)],
           llm="gpt-4o-mini",
           max_iter=40  # Increased iterations to allow for more thorough research
       )


   @task
   def discovery_task(self) -> Task:
       """Creates the task for discovering family offices in Chicago"""
       return Task(
           config=self.tasks_config['discovery_task']
       )


   @task
   def profile_scraper_task(self) -> Task:
       """Creates the task for building family office profiles"""
       return Task(
           config=self.tasks_config['profile_scraper_task']
       )  
   
   @task
   def news_scraper_task(self) -> Task:
       """Creates the task for scraping news about family offices"""
       return Task(
           config=self.tasks_config['news_scraper_task']
       )
          
   @crew
   def crew(self) -> Crew:
       """Creates the Family Office Finder crew"""
       return Crew(
           agents=[
               self.family_office_discovery_agent(),
               self.family_office_profile_agent(),
               self.family_office_news_agent()
           ],
           tasks=[
               self.discovery_task(),
               self.profile_scraper_task(),
               self.news_scraper_task()
           ],
           process=Process.sequential,
           verbose=True,
           memory=True
       )