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
           Crawls an entire website to extract comprehensive information including contact details.
           
           Args:
               url: The website URL to crawl
               
           Returns:
               The extracted website content including contact information
           """
           import requests
           
           headers = {
               "Authorization": f"Bearer {firecrawl_api_key}",
               "Content-Type": "application/json"
           }
           
           payload = {
               "url": url,
               "max_pages": 15,  # Crawl up to 15 pages
               "include_contact_info": True,
               "follow_links": True,
               "follow_subdomains": False,
               "follow_link_keywords": ["contact", "about", "team", "leadership", "people", "professionals", "our-team"],
               "extract_emails": True,
               "extract_phone_numbers": True,
               "extract_addresses": True,
               "extract_social_media": True
           }
           
           response = requests.post(
               "https://api.firecrawl.dev/v1/crawl",
               headers=headers,
               json=payload
           )
           
           if response.status_code == 200:
               result = response.json()
               # Format the response for better readability
               content = f"Website: {url}\n\n"
               
               # Add contact information if available
               if "contact_info" in result and result["contact_info"]:
                   content += "CONTACT INFORMATION:\n"
                   contact_info = result["contact_info"]
                   
                   if "emails" in contact_info and contact_info["emails"]:
                       content += f"Emails: {', '.join(contact_info['emails'])}\n"
                   
                   if "phone_numbers" in contact_info and contact_info["phone_numbers"]:
                       content += f"Phone Numbers: {', '.join(contact_info['phone_numbers'])}\n"
                   
                   if "addresses" in contact_info and contact_info["addresses"]:
                       content += f"Addresses: {', '.join(contact_info['addresses'])}\n"
                   
                   if "social_media" in contact_info and contact_info["social_media"]:
                       content += "Social Media:\n"
                       for platform, url in contact_info["social_media"].items():
                           content += f"- {platform}: {url}\n"
                   
                   content += "\n"
               
               # Add page content
               if "pages" in result and result["pages"]:
                   content += "WEBSITE CONTENT:\n\n"
                   for page in result["pages"]:
                       content += f"Page: {page['url']}\n"
                       content += f"Title: {page.get('title', 'No title')}\n"
                       content += f"Content:\n{page.get('content', 'No content')}\n\n"
                       content += "---\n\n"
               
               return content
           else:
               return f"Error crawling website: {response.status_code} - {response.text}"
       
       # Also keep the original scrape tool for specific pages
       scrape_tool = FirecrawlScrapeWebsiteTool(
           api_key=firecrawl_api_key,
           params={
               'formats': ['markdown', 'html'],
               'include_links': True,
               'include_images': False,
               'include_contact_info': True,
               'max_pages': 1,
           }
       )
       
       return Agent(
           config=self.agents_config['family_office_profile_agent'],
           verbose=True,
           tools=[firecrawl_crawl_tool, scrape_tool],
           llm="gpt-4o",  # Upgraded to full GPT-4o for better processing
           max_iter=80,  # Increased iterations to handle multiple family offices
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