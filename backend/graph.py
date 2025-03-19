from langgraph.graph import StateGraph, add_messages,  END
from langgraph.checkpoint.memory import MemorySaver
from backend.orchestrator_agent.orchestrator import Orchestrator, orchestrator_action, orchestrator_router
from backend.reasoning_agent.reasoning import Reasoning, ReasoningOrchestrator, reasoning_completion
from backend.reasoning_agent.config import CONFIG as REASONING_CONFIG
from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict
import asyncio
from typing import List, Optional
import operator

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
    graph = StateGraph(State)
    graph.add_node(Orchestrator.name, Orchestrator(llm=ChatOpenAI(model="gpt-4o")))
    graph.add_node("orchestrator_action", orchestrator_action)
    reasoning_orchestrator = ReasoningOrchestrator(llm=ChatOpenAI(model="gpt-4o"))
    graph.add_node(ReasoningOrchestrator.name, reasoning_orchestrator)
    graph.add_node('reasoning_completion', reasoning_completion)
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
    return graph

# Create and compile the graph for use by the websocket implementation
graph = create_graph()
memory = MemorySaver()
workflow = graph.compile(checkpointer=memory)

async def run(app):
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
    

if __name__ == "__main__":
    graph = create_graph() 
    memory = MemorySaver()
    app  = graph.compile(checkpointer=memory)
    asyncio.run(run(app))




