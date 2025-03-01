from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
    SerperDevTool, 
    EXASearchTool, 
    FirecrawlScrapeWebsiteTool,
    FirecrawlCrawlWebsiteTool
)

@CrewBase
class MAAgentsCrew():
    """M&A Agent Crew for sell-side M&A processes"""

    @agent
    def discovery_agent(self) -> Agent:
        """Creates the Discovery Agent for finding potential buyers"""
        return Agent(
            config=self.agents_config['discovery_agent'],
            verbose=True,
            tools=[EXASearchTool(), SerperDevTool()],
            llm="gpt-4o-mini"  # Using a capable model for complex research
        )

    @agent
    def profile_scraper_agent(self) -> Agent:
        """Creates the Profile Scraper Agent for building buyer profiles"""
        return Agent(
            config=self.agents_config['profile_scraper_agent'],
            verbose=True,
            tools=[FirecrawlScrapeWebsiteTool(), FirecrawlCrawlWebsiteTool()],
            llm="gpt-4o-mini"
        )

    @agent
    def news_scraper_agent(self) -> Agent:
        """Creates the News Scraper Agent for gathering media information"""
        return Agent(
            config=self.agents_config['news_scraper_agent'],
            verbose=True,
            tools=[SerperDevTool(), EXASearchTool()],
            llm="gpt-4o-mini"
        )

    @task
    def discovery_task(self) -> Task:
        """Creates the task for discovering potential buyers"""
        return Task(
            config=self.tasks_config['discovery_task']
        )

    @task
    def profile_scraper_task(self) -> Task:
        """Creates the task for building buyer profiles"""
        return Task(
            config=self.tasks_config['profile_scraper_task']
        )

    @task
    def news_scraper_task(self) -> Task:
        """Creates the task for gathering news and media information"""
        return Task(
            config=self.tasks_config['news_scraper_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the M&A Agents crew with sequential processing"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True
        )