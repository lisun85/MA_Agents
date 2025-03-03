import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import EXASearchTool, FirecrawlScrapeWebsiteTool
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
        """Creates the Family Office Profile Agent"""
        # Get the Firecrawl API key from environment variables
        firecrawl_api_key = os.environ.get("FIRECRAWL_API_KEY")
        
        # Ensure the API key is available
        if not firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is not set")
        
        return Agent(
            config=self.agents_config['family_office_profile_agent'],
            verbose=True,
            tools=[FirecrawlScrapeWebsiteTool(api_key=firecrawl_api_key)],
            llm="gpt-4o-mini",
            max_iter=25
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
        	
    @crew
    def crew(self) -> Crew:
        """Creates the Family Office Finder crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True
        )