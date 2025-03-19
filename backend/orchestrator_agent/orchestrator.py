from pydantic import BaseModel
from langgraph.graph import END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage
from .tools import get_company_info
from typing import Dict, Any
from dotenv import load_dotenv
from .prompts import PROMPT

load_dotenv()

class Orchestrator:
    name = 'orchestrator'
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", PROMPT),
            MessagesPlaceholder(variable_name="messages")
        ])
        self.prompt = self.prompt.partial(tools = [get_company_info])
        self.chain = self.prompt | self.llm.bind_tools([get_company_info])

    def __call__(self, state) -> Dict[str, Any]:
        self.initialize_state(state)
        if state["sector"] and state["check_size"] and state["geographical_location"]:
            response = self.chain.invoke({"messages": state["messages"]})
            return {"messages": [response]}
        else:
            print("messages****") #, state["messages"][-1])
            return {}
    
    def initialize_state(self, state):
        if "urls" not in state or not isinstance(state["urls"], list) or len(state["urls"]) == 0:
            state["urls"] = []
            state["reasoning_completed"] = False
        

def orchestrator_action(state):
    last_message = state["messages"][-1]
    messages = []
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "get_company_info":
                company_info = get_company_info(tool_call["args"]["query"])
                tool_message = ToolMessage(
                    content=f"Content: {company_info}",
                    name="get_company_info",
                    tool_call_id=tool_call["id"],
                )
                messages.append(tool_message)

    return {"messages": messages}
    
def orchestrator_router(state):
    print(f"DEBUG ROUTER - State keys: {state.keys()}")
    print(f"DEBUG ROUTER - reasoning_completed: {state.get('reasoning_completed', 'Not Found')}")
    print(f"DEBUG ROUTER - sector: {state.get('sector', 'Not Found')}")
    print(f"DEBUG ROUTER - check_size: {state.get('check_size', 'Not Found')}")
    print(f"DEBUG ROUTER - geographical_location: {state.get('geographical_location', 'Not Found')}")
    
    if state["messages"] and hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls:
        print("DEBUG ROUTER - Routing to orchestrator_action")
        return "orchestrator_action"
    elif not state.get("reasoning_completed", False) and state.get("sector") and state.get("check_size") and state.get("geographical_location"):
        print("DEBUG ROUTER - Routing to reasoning_orchestrator")
        return "reasoning_orchestrator"
    else:
        print("DEBUG ROUTER - Routing to END")
        return END


    
