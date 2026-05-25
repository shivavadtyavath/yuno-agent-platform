from langchain_core.tools import tool, BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, END, MessagesState

@tool
def calc(expression: str) -> str:
    """Calculate math."""
    return str(eval(expression))

llm = ChatOpenAI(api_key='test-key')
llm_with_tools = llm.bind_tools([calc])
print("bind_tools OK")

# Test StateGraph with MessagesState (LangGraph 1.x style)
from typing import Annotated
import operator
from typing import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

g = StateGraph(AgentState)
print("StateGraph with custom TypedDict OK")

# Test MessagesState
g2 = StateGraph(MessagesState)
print("StateGraph with MessagesState OK")

# Test tool execution
from langchain_core.messages import ToolMessage
tool_result = calc.invoke({"expression": "2+2"})
print(f"Tool execution OK: {tool_result}")

print("\nAll checks passed!")
