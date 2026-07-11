from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
import pandas as pd

load_dotenv()

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

parser = JsonOutputParser()


def create_dashboard_layout(
    components: list,
    datasets: dict
):
    """
    Generates the final dashboard layout.

    Parameters
    ----------
    components : list
        Components containing SQL queries.

    datasets : dict
        Dictionary mapping component ids to DataFrames.

    Returns
    -------
    list
        Components enriched with visualization information.
    """

    component_info = []

    for component in components:

        df = datasets[component["id"]]

        component_info.append({

            "id": component["id"],

            "title": component["title"],

            "type": component["type"],

            "columns": list(df.columns),

            "sample_data": df.head(5).to_dict("records")
        })

    prompt = f"""
You are an expert dashboard designer.

Your task is to decide the BEST visualization for every dashboard component.

Return ONLY valid JSON.

Component Information:

{component_info}

For every component return:

[
    {{
        "id":"component_1",

        "title":"Monthly Revenue",

        "type":"chart",

        "chart_type":"line",

        "x":"Month",

        "y":"Revenue"
    }}
]
"""

    response = model.invoke(prompt)

    return parser.parse(response.content)