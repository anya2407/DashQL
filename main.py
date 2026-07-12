from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
from nodes.retreival import search_dashboard, index_dashboard
from agents.planner import create_dashboard_plan
from tools.check_schema import get_full_schema
from agents.sql_generator import generate_sql
from tools.database import execute_sql
from agents.visualizer import create_dashboard_layout
from tools.github import save_dashboard_to_github, load_dashboard_from_github
import sqlite3
import uuid
import datetime

load_dotenv()

# -------------------------
# Shared Graph State
# -------------------------

class DashState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    request: str
    dashboard_found: bool
    dashboard_id: str
    dashboard_plan: list
    sql_queries: list
    datasets: dict
    dashboard_layout: list
    answer: str
    progress: str


# -------------------------
# Nodes
# -------------------------

def retrieval_node(state: DashState):
    dashboard_id = search_dashboard(state["request"])

    if dashboard_id is None:
        return {
            "progress": "🔍 No matching dashboard found, generating fresh...",
            "dashboard_found": False
        }

    return {
        "progress": "⚡ Found a matching dashboard, loading...",
        "dashboard_found": True,
        "dashboard_id": dashboard_id
    }


def load_from_cache_node(state: DashState):
    dashboard_data = load_dashboard_from_github(state["dashboard_id"])

    if dashboard_data is None:
        # Safety fallback: Chroma said there's a match, but GitHub fetch
        # failed. Treat it as a miss instead of crashing.
        return {
            "progress": "⚠️ Cache entry was stale, generating fresh instead...",
            "dashboard_found": False
        }

    return {
        "progress": "⚡ Loaded cached dashboard, refreshing data...",
        "dashboard_layout": dashboard_data["dashboard_layout"],
        "sql_queries": dashboard_data["sql_queries"]
    }


def planner_node(state: DashState):
    schema = get_full_schema()
    plan = create_dashboard_plan(state["request"], schema)
    return {
        "progress": "🧠 Planning dashboard...",
        "dashboard_plan": plan
    }


def sql_generator_node(state: DashState):
    schema = get_full_schema()
    components = generate_sql(state["dashboard_plan"], schema)
    return {
        "progress": "📝 Generating SQL...",
        "sql_queries": components
    }


def sql_executor_node(state: DashState):
    datasets = {}
    for component in state["sql_queries"]:
        df = execute_sql(component["sql"])
        datasets[component["id"]] = df.to_dict("records")
    return {
        "progress": "🗄 Executing SQL...",
        "datasets": datasets
    }


def visualization_node(state: DashState):
    layout = create_dashboard_layout(state["sql_queries"], state["datasets"])
    return {
        "progress": "📊 Designing dashboard...",
        "dashboard_layout": layout
    }


def save_to_cache_node(state: DashState):
    dashboard_id = f"dashboard_{uuid.uuid4().hex[:8]}"

    dashboard_data = {
        "dashboard_id": dashboard_id,
        "request": state["request"],
        "dashboard_layout": state["dashboard_layout"],
        "sql_queries": state["sql_queries"],
        "timestamp": datetime.datetime.now().isoformat()
    }

    save_dashboard_to_github(dashboard_id, dashboard_data)
    index_dashboard(dashboard_id, state["request"])

    return {
        "progress": "💾 Dashboard saved for future reuse...",
        "dashboard_id": dashboard_id
    }


# -------------------------
# Routing
# -------------------------

def route_after_retrieval(state: DashState):
    if state["dashboard_found"]:
        return "load_from_cache"
    return "planner"


def route_after_cache_load(state: DashState):
    # load_from_cache_node might have flipped dashboard_found to False
    # if the GitHub fetch failed (stale cache entry)
    if state["dashboard_found"]:
        return "sql_executor"
    return "planner"


# -------------------------
# Graph
# -------------------------

graph = StateGraph(DashState)

graph.add_node("retrieval", retrieval_node)
graph.add_node("load_from_cache", load_from_cache_node)
graph.add_node("planner", planner_node)
graph.add_node("sql_generator", sql_generator_node)
graph.add_node("sql_executor", sql_executor_node)
graph.add_node("visualization", visualization_node)
graph.add_node("save_to_cache", save_to_cache_node)

graph.add_edge(START, "retrieval")

graph.add_conditional_edges(
    "retrieval",
    route_after_retrieval,
    {"load_from_cache": "load_from_cache", "planner": "planner"}
)

graph.add_conditional_edges(
    "load_from_cache",
    route_after_cache_load,
    {"sql_executor": "sql_executor", "planner": "planner"}
)

graph.add_edge("planner", "sql_generator")
graph.add_edge("sql_generator", "sql_executor")

# sql_executor now has two possible next steps depending on how we got here:
# - came from cache (load_from_cache) -> go straight to END, skip visualization
# - came from fresh generation (planner path) -> go to visualization, then save

def route_after_execution(state: DashState):
    # If dashboard_layout is already set, we came from cache -> done
    if state.get("dashboard_layout"):
        return "end"
    return "visualization"

graph.add_conditional_edges(
    "sql_executor",
    route_after_execution,
    {"end": END, "visualization": "visualization"}
)

graph.add_edge("visualization", "save_to_cache")
graph.add_edge("save_to_cache", END)


# -------------------------
# Memory
# -------------------------

conn = sqlite3.connect("dashql.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
chatbot = graph.compile(checkpointer=checkpointer)