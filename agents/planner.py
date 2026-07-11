from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import json

load_dotenv()

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

parser = JsonOutputParser()


def create_dashboard_plan(
    user_request: str,
    schema: str
):
    """
    Generates a dashboard plan from the user's request.

    Parameters
    ----------
    user_request : str
        Natural language dashboard request.

    schema : str
        Database schema.

    Returns
    -------
    list
        Dashboard plan.
    """

    prompt = f"""
You are an expert Business Intelligence dashboard planner.

Your task is ONLY to decide what components should appear on the dashboard.

DO NOT generate SQL.

DO NOT explain anything.

Return ONLY valid JSON.

Database Schema:

{schema}

User Request:

{user_request}

Return JSON in this format:

[
    {{
        "id":"component_1",
        "title":"Monthly Revenue",
        "type":"chart",
        "description":"Monthly revenue trend"
    }},
    {{
        "id":"component_2",
        "title":"Top Customers",
        "type":"table",
        "description":"Highest spending customers"
    }},
    {{
        "id":"component_3",
        "title":"Total Revenue",
        "type":"kpi",
        "description":"Overall revenue"
    }}
]
"""

    response = model.invoke(prompt)

    return parser.parse(response.content)