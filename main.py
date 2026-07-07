from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
from tools.check_schema import get_full_schema
from tools.sqltools import run_sql
from langgraph.prebuilt import ToolNode, tools_condition
import sqlite3

load_dotenv()

class ChatState(TypedDict):
    message: Annotated[list[BaseMessage],add_messages]

model=ChatGoogleGenerativeAI(model="gemini-2.5-flash",temperature=0)
model_with_tools = model.bind_tools([get_full_schema,run_sql])

def chat_node(state:ChatState):
    message=state['message']
    resp=model_with_tools.invoke(message)
    return {'message':[resp]}

tool_node = ToolNode([get_full_schema, run_sql])

graph=StateGraph(ChatState)

graph.add_node('chat_node',chat_node)
graph.add_node('tools', tool_node)

graph.add_edge(START,'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)  # routes to 'tools' or END automatically
graph.add_edge('tools', 'chat_node')

conn = sqlite3.connect('dashql.db', check_same_thread=False)

checkpointer=SqliteSaver(conn=conn)
chatbot=graph.compile(checkpointer=checkpointer) 



