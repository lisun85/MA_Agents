from pydantic import BaseModel
from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage
from tools import get_company_info
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Orchestrator:
    name = 'orchestrator'
    
    def __init__(self, llm, prompt):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", prompt),
            MessagesPlaceholder(variable_name="messages")
        ])
        self.chain = self.prompt | self.llm

    def __call__(self, state: StateGraph) -> Dict[str, Any]:
        response = self.model.invoke(state["messages"])
        state["messages"].append(response)
        return state
    
def orchestrator_action(state: StateGraph) -> StateGraph:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.name == "get_company_info":
                company_info = get_company_info(tool_call.args["query"])
                tool_message = ToolMessage(
                    content=f"{company_info}",
                    name="get_company_info",
                    tool_call_id=tool_call.id,
                )
                state["messages"].append(tool_message)
        return state
    else:
        return state


    
