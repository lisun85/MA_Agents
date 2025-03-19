from langchain_core.prompts import PromptTemplate
from typing import Dict, Any
from dotenv import load_dotenv
from .prompts import PROMPT
from .config import CONFIG 

load_dotenv()

def retrieve_company_info(url):
    print(f"DEBUG - Retrieving company info from {url}")
    return "Company Info" # this should be AWS access to S3 bucket, need to chunk data and into vector db?

class ReasoningOrchestrator:
    name = 'reasoning_orchestrator'
    
    def __init__(self, llm):
        print("DEBUG - Initializing ReasoningOrchestrator")
        self.urls = CONFIG["urls"]
        self.agent_size = CONFIG["agent_size"]
        self.agents = []
        
        # Calculate how many URLs each agent should handle
        urls_per_agent = len(self.urls) // self.agent_size
        remainder = len(self.urls) % self.agent_size
        
        # Distribute URLs as evenly as possible among agents
        start_idx = 0
        for i in range(self.agent_size):
            # Give one extra URL to the first 'remainder' agents
            agent_url_count = urls_per_agent + (1 if i < remainder else 0)
            end_idx = start_idx + agent_url_count
            
            # Assign this slice of URLs to a new Reasoning agent
            agent_urls = self.urls[start_idx:end_idx]
            self.agents.append(Reasoning(llm=llm, urls=agent_urls))
            
            start_idx = end_idx
        print(f"DEBUG - Created {len(self.agents)} reasoning agents")

    def __call__(self, state) -> Dict[str, Any]:
        print(f"DEBUG - ReasoningOrchestrator called with state: {state}")
        return state

class Reasoning:
    name = 'reasoning'
    
    def __init__(self, llm, urls):
        print(f"DEBUG - Initializing Reasoning agent with {len(urls)} URLs")
        self.llm = llm
        self.prompt = PromptTemplate.from_template(PROMPT)
        self.urls = urls

    def __call__(self, state) -> Dict[str, Any]:
        print(f"DEBUG - Reasoning agent called with state: {state}")
        urls = []
        for url in self.urls:
            print(f"DEBUG - Processing URL: {url}")
            company_info = retrieve_company_info(url)
            prompt = self.prompt.partial(
                company_info=company_info,
                sector=state["sector"],
                check_size=state["check_size"],
                geographical_location=state["geographical_location"]
            )
            chain = prompt | self.llm
            print(f"DEBUG - Invoking LLM for URL: {url}")
            response = chain.invoke(state)
            print(f"DEBUG - LLM response for URL {url}: {response}")
            if response == "yes":
                urls.append(url)
        print(f"DEBUG - Reasoning agent returning URLs: {urls}")
        return {"urls": urls}

def reasoning_completion(state):
    print(f"DEBUG - reasoning_completion called with state: {state}")
    return {"reasoning_completed": True}
  

    