from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import pandas as pd


class DashState(TypedDict):
    """
    Shared state for the entire LangGraph workflow.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    request: str
    dashboard_plan: list
    datasets: dict[str, pd.DataFrame]
    dashboard_layout: dict
    answer: str