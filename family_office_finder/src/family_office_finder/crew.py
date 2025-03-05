import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import EXASearchTool, FirecrawlScrapeWebsiteTool, SerperDevTool
from dotenv import load_dotenv
from langchain.tools import tool


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
       """Creates the Family Office Profile Agent with website crawling capabilities"""
       # Get the Firecrawl API key from environment variables
       firecrawl_api_key = os.environ.get("FIRECRAWL_API_KEY")
       
       # Ensure the API key is available
       if not firecrawl_api_key:
           raise ValueError("FIRECRAWL_API_KEY environment variable is not set")
       
       @tool("firecrawl_crawl_tool")
       def firecrawl_crawl_tool(url: str) -> str:
           """
           Crawls a website using Firecrawl API to extract content.
           Input should be a valid URL.
           """
           try:
               # Create an instance of the FirecrawlScrapeWebsiteTool
               firecrawl_tool = FirecrawlScrapeWebsiteTool(api_key=firecrawl_api_key)
               
               # Call the tool with the URL
               result = firecrawl_tool(url)
               
               # Return the result
               return result
           except Exception as e:
               return f"Error crawling website: {str(e)}"
       
       @tool("scrape_tool")
       def scrape_tool(url: str) -> str:
           """
           Scrapes a specific page from a website to extract information.
           Input should be a valid URL.
           """
           try:
               # Create an instance of the FirecrawlScrapeWebsiteTool
               firecrawl_tool = FirecrawlScrapeWebsiteTool(api_key=firecrawl_api_key)
               
               # Call the tool with the URL
               result = firecrawl_tool(url)
               
               # Return the result
               return result
           except Exception as e:
               return f"Error scraping page: {str(e)}"
       
       return Agent(
           config=self.agents_config['family_office_profile_agent'],
           verbose=True,
           tools=[firecrawl_crawl_tool, scrape_tool],
           llm="gpt-4o-mini",  # Changed from gpt-4o to gpt-4o-mini to reduce token usage
           max_iter=30,  # Reduced from 80 to 30 to limit token consumption
           temperature=0.2  # Lower temperature for more consistent output
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
           max_iter=40,  # Increased iterations to allow for more thorough research
           temperature=0.2  # Lower temperature for more consistent output
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