from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()

class ChatState(TypedDict):
    message: Annotated[list[BaseMessage],add_messages]

model=ChatGoogleGenerativeAI(model="gemini-2.5-flash",temperature=0)

def chat_node(state:ChatState):
    message=state['message']
    resp=model.invoke(message)
    return {'message':[resp]}

graph=StateGraph(ChatState)
graph.add_node('chat_node',chat_node)
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

checkpointer=MemorySaver()
chatbot=graph.compile(checkpointer=checkpointer) 

stream=chatbot.stream(
    {'message':[HumanMessage(content='what is the recipe to make pasta')]},
    config={'configurable':{'thread_id':'thread-1'}},
    stream_mode='messages'
)


