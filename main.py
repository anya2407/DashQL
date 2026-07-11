from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
from nodes.retrieval import search_dashboard
from agents.planner import create_dashboard_plan
from tools.check_schema import get_full_schema
from agents.sql_generator import generate_sql
from nodes.sql_executor import execute_dashboard_queries
from agents.visualizer import create_dashboard_layout
import sqlite3

load_dotenv()

# -------------------------
# Shared Graph State
# -------------------------

class DashState(TypedDict):

    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Original request
    request: str

    # Retrieval
    dashboard_found: bool
    retrieved_dashboard: dict

    # Planner Output
    dashboard_plan: list

    # SQL Generator Output
    sql_queries: list

    # SQL Executor Output
    datasets: dict

    # Visualization Output
    dashboard_layout: dict

    # Final response
    answer: str

    progress: str



# -------------------------
# Nodes
# -------------------------

def retrieval_node(state: DashState):

    dashboard = search_dashboard(
        state["request"]
    )

    if dashboard is None:

        return {
            "dashboard_found": False
        }

    return {

        "dashboard_found": True,

        "retrieved_dashboard": dashboard
    }


def planner_node(state: DashState):

    schema = get_full_schema()

    plan = create_dashboard_plan(
        state["request"],
        schema
    )

    return {

    "progress":"🧠 Planning dashboard...",

    "dashboard_plan": plan

    }


def sql_generator_node(state: DashState):

    schema = get_full_schema()

    components = generate_sql(
        state["dashboard_plan"],
        schema
    )

    return {

    "progress":"📝 Generating SQL...",

    "sql_queries": components

    }


def sql_executor_node(state: DashState):

    components, datasets = execute_dashboard_queries(
        state["sql_queries"]
    )

    return {

    "progress":"🗄 Executing SQL...",

    "datasets": datasets,

    "sql_queries": components

    }


def visualization_node(state: DashState):

    layout = create_dashboard_layout(
        state["sql_queries"],
        state["datasets"]
    )

    return {

    "progress":"📊 Designing dashboard...",

    "dashboard_layout": layout

    }


# -------------------------
# Graph
# -------------------------

graph = StateGraph(DashState)

graph.add_node("retrieval", retrieval_node)
graph.add_node("planner", planner_node)
graph.add_node("sql_generator", sql_generator_node)
graph.add_node("sql_executor", sql_executor_node)
graph.add_node("visualization", visualization_node)

graph.add_edge(START, "retrieval")
graph.add_edge("retrieval", "planner")
graph.add_edge("planner", "sql_generator")
graph.add_edge("sql_generator", "sql_executor")
graph.add_edge("sql_executor", "visualization")
graph.add_edge("visualization", END)


# -------------------------
# Memory
# -------------------------

conn = sqlite3.connect(
    "dashql.db",
    check_same_thread=False
)

checkpointer = SqliteSaver(conn)

chatbot = graph.compile(
    checkpointer=checkpointer
)