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
from tools.governance import check_all_components
from agents.insights import generate_insights
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
    governance_attempts: int


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


MAX_GOVERNANCE_RETRIES = 2

def governance_node(state: DashState):
    result = check_all_components(state["sql_queries"])

    if result["passed"]:
        return {
            "progress": "🛡️ Governance check passed...",
        }

    attempts = state.get("governance_attempts", 0) + 1

    violation_summary = "; ".join(
        f"Component {f['id']}: {', '.join(f['violations'])}"
        for f in result["failed_components"]
    )

    return {
        "progress": f"⚠️ Governance check failed (attempt {attempts}): {violation_summary}",
        "governance_attempts": attempts,
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


def insights_node(state: DashState):
    insight_text = generate_insights(
        state["request"],
        state["sql_queries"],
        state["datasets"]
    )
    return {
        "progress": "💡 Generating insights...",
        "answer": insight_text
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


def governance_fail_node(state: DashState):
    return {
        "progress": "❌ Could not generate a compliant dashboard after multiple attempts.",
        "answer": "I wasn't able to generate a dashboard that meets data governance rules. Try rephrasing your request.",
        "dashboard_layout": [],
        "datasets": {},
    }


# -------------------------
# Routing (function definitions only — no graph calls here)
# -------------------------

def route_after_retrieval(state: DashState):
    if state["dashboard_found"]:
        return "load_from_cache"
    return "planner"


def route_after_cache_load(state: DashState):
    if state["dashboard_found"]:
        return "sql_executor"
    return "planner"


def route_after_governance(state: DashState):
    result = check_all_components(state["sql_queries"])

    if result["passed"]:
        return "sql_executor"

    if state.get("governance_attempts", 0) >= MAX_GOVERNANCE_RETRIES:
        return "fail"

    return "sql_generator"


def route_after_execution(state: DashState):
    if state.get("dashboard_layout"):
        return "insights"
    return "visualization"


def route_after_insights(state: DashState):
    if state.get("dashboard_id"):
        return "end"
    return "save_to_cache"


# -------------------------
# Graph (all graph.* calls live here, in order)
# -------------------------

graph = StateGraph(DashState)

graph.add_node("retrieval", retrieval_node)
graph.add_node("load_from_cache", load_from_cache_node)
graph.add_node("planner", planner_node)
graph.add_node("sql_generator", sql_generator_node)
graph.add_node("governance", governance_node)
graph.add_node("governance_fail", governance_fail_node)
graph.add_node("sql_executor", sql_executor_node)
graph.add_node("visualization", visualization_node)
graph.add_node("insights", insights_node)
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
graph.add_edge("sql_generator", "governance")

graph.add_conditional_edges(
    "governance",
    route_after_governance,
    {"sql_executor": "sql_executor", "sql_generator": "sql_generator", "fail": "governance_fail"}
)

graph.add_edge("governance_fail", END)

graph.add_conditional_edges(
    "sql_executor",
    route_after_execution,
    {"insights": "insights", "visualization": "visualization"}
)

graph.add_edge("visualization", "insights")

graph.add_conditional_edges(
    "insights",
    route_after_insights,
    {"save_to_cache": "save_to_cache", "end": END}
)

graph.add_edge("save_to_cache", END)


# -------------------------
# Memory
# -------------------------

conn = sqlite3.connect("dashql.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
chatbot = graph.compile(checkpointer=checkpointer)