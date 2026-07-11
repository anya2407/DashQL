from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

parser = JsonOutputParser()


def generate_sql(
    dashboard_plan: list,
    schema: str
):
    """
    Adds SQL queries to every dashboard component.

    Parameters
    ----------
    dashboard_plan : list
        Planner output.

    schema : str
        Database schema.

    Returns
    -------
    list
        Same dashboard plan with SQL added.
    """

    prompt = f"""
You are an expert SQL developer.

Database Schema

{schema}

Dashboard Components

{dashboard_plan}

For EVERY component generate exactly one SQL query.

Return ONLY valid JSON.

Example format:

[
    {{
        "id":"component_1",
        "title":"Monthly Revenue",
        "type":"chart",
        "description":"Monthly revenue",

        "sql":"SELECT ..."

    }}
]
"""

    response = model.invoke(prompt)

    return parser.parse(response.content)