import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, EXASearchTool

EXA_API_KEY = os.getenv('EXA_API_KEY')

@CrewBase
class MAAgentsCrew():
    """M&A Agent Crew for sell-side M&A processes"""

    @agent
    def discovery_agent(self) -> Agent:
        """Creates the Discovery Agent for finding potential buyers"""
        return Agent(
            config=self.agents_config['discovery_agent'],
            verbose=True,
            tools=[SerperDevTool()],  # Remove EXASearchTool temporarily
            llm="gpt-4o-mini"  # Using a capable model for complex research
        )

    @task
    def discovery_task(self) -> Task:
        """Creates the task for discovering potential buyers"""
        return Task(
            config=self.tasks_config['discovery_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the M&A Agents crew with a single agent"""
        return Crew(
            agents=[self.discovery_agent()],
            tasks=[self.discovery_task()],
            process=Process.sequential,
            verbose=True
        )