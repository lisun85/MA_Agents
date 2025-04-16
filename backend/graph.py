import argparse
from langgraph.graph import StateGraph, add_messages, END
from langgraph.checkpoint.memory import MemorySaver
from backend.orchestrator_agent.orchestrator import Orchestrator, orchestrator_action, orchestrator_router
from backend.reasoning_agent.reasoning import Reasoning, ReasoningOrchestrator, reasoning_completion
from backend.reasoning_agent.config import CONFIG as REASONING_CONFIG
from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict
import asyncio
from typing import List, Optional
import operator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('graph.log')
    ]
)
logger = logging.getLogger(__name__)

# Custom append function for merging lists
def append(left: Optional[List] = None, right: Optional[List] = None):
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right

class State(TypedDict):
    messages: Annotated[list, add_messages]
    sector: str
    check_size: str
    geographical_location: str
    urls: Annotated[list, operator.add]
    reasoning_completed: bool
    
def create_graph() -> StateGraph:
    logger.info("Creating LangGraph workflow for DeepSeek reasoning")
    
    graph = StateGraph(State)
    graph.add_node(Orchestrator.name, Orchestrator(llm=ChatOpenAI(model="gpt-4o", temperature=0)))
    graph.add_node("orchestrator_action", orchestrator_action)
    
    # Create the ReasoningOrchestrator with the specified number of agents
    reasoning_orchestrator = ReasoningOrchestrator()
    graph.add_node(ReasoningOrchestrator.name, reasoning_orchestrator)
    graph.add_node('reasoning_completion', reasoning_completion)
    
    # Add each reasoning agent to the graph
    for i, ra in enumerate(reasoning_orchestrator.agents):
        graph.add_node(f'reasoning{i}', ra)
        graph.add_edge(ReasoningOrchestrator.name, f'reasoning{i}')
        graph.add_edge(f'reasoning{i}', 'reasoning_completion')
    
    graph.add_edge("orchestrator_action", Orchestrator.name)
    graph.add_conditional_edges(
        Orchestrator.name,
        orchestrator_router
    )
    graph.set_entry_point(Orchestrator.name)
    
    logger.info(f"Graph created with {len(reasoning_orchestrator.agents)} reasoning agents")
    return graph

# Create and compile the graph for use
graph = create_graph()
memory = MemorySaver()
workflow = graph.compile(checkpointer=memory)

async def run_interactive(app):
    from langchain_core.messages import AIMessageChunk, HumanMessage
    config = {"configurable": {"thread_id": 1}}
    _user_input = input("User: ")

    while _user_input != "quit":
        out=""
        astream = app.astream({"messages": [HumanMessage(content=_user_input)], "fields":"full name, birthdate", "values":"John Doe, 1990-01-01"}, config=config, stream_mode="messages")
        async for msg, metadata in astream:
            if isinstance(msg, AIMessageChunk):
                out+=msg.content
        print('Assistant: ', out)
        _user_input = input("User: ")

async def process_documents():
    """
    Run the workflow in document processing mode. This bypasses the interactive mode and directly runs the reasoning orchestration.
    """
    logger.info("Starting document processing with LangGraph workflow")
    
    # Initial state with instruction to process documents
    initial_state = {
        "messages": [{
            "role": "user", 
            "content": "Process all company documents from S3."
        }],
        "sector": REASONING_CONFIG["default_values"]["sector"],
        "check_size": REASONING_CONFIG["default_values"]["check_size"],
        "geographical_location": REASONING_CONFIG["default_values"]["geographical_location"],
        "urls": [],
        "reasoning_completed": False
    }
    
    # Run the workflow with this initial state
    config = {"configurable": {"thread_id": 2}}
    result = workflow.invoke(initial_state, config=config)
    
    logger.info("Document processing workflow completed")
    
    # Check if reasoning was completed
    if result.get("reasoning_completed", False):
        print("✅ Successfully processed all company documents!")
    else:
        print("❌ Document processing did not complete successfully.")
    
    # Print any results or messages
    if "stats" in result:
        stats = result["stats"]
        print(f"📊 Stats: Processed {stats.get('processed', 0)} documents, "
              f"Success: {stats.get('successful', 0)}, "
              f"Failed: {stats.get('failed', 0)}")
    
    print("🔍 Check the output directory for results.")
    return result

def parse_args():
    parser = argparse.ArgumentParser(description="Run reasoning orchestrator")
    parser.add_argument("--process", action="store_true", help="Process S3 documents")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if args.process:
        # Run in document processing mode
        asyncio.run(process_documents())
    elif args.interactive:
        # Run in interactive mode
        graph = create_graph() 
        memory = MemorySaver()
        app = graph.compile(checkpointer=memory)
        asyncio.run(run_interactive(app))
    else:
        # Default to document processing
        print("No mode specified, defaulting to document processing.")
        asyncio.run(process_documents())




