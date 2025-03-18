from langgraph.graph import StateGraph
from langgraph.graph import add_message
from orchestrator_agent.orchestrator import Orchestrator, orchestrator_action, orchestrator_router
from langgraph.graph import StateGraph, END

from typing_extensions import Annotated, TypedDict

class State(TypedDict):
    messages: Annotated[list, add_message]
    completed: bool
    
def create_graph() -> StateGraph:
    graph = StateGraph(State)
    graph.add_node("orchestrator", Orchestrator)
    graph.add_node("orchestrator_action", orchestrator_action)
    graph.add_edge("START", "orchestrator")
    graph.add_edge("orchestrator_action", END)
    graph.set_entry_point("orchestrator")
    return graph




