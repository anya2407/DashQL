from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
import pandas as pd

load_dotenv()

model = ChatOpenAI(
    model="gpt-4o-mini",
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

        df = pd.DataFrame(datasets[component["id"]])

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

Return ONLY valid JSON. Include EVERY component from the input, even if unchanged.

Component Information:

{component_info}

Rules:

- For components with type "chart": choose chart_type ('line', 'bar', 'pie', or 'scatter')
  and appropriate x/y columns based on the sample_data and columns provided.

- For components with type "table": return them UNCHANGED. Do NOT add chart_type, x, or y fields.

- For components with type "kpi": return them UNCHANGED. Do NOT add chart_type, x, or y fields.

- Every component's "id" must exactly match the id given in Component Information.
  Do not rename, drop, or add ids.

Example output format:

[
    {{
        "id":"component_1",
        "title":"Monthly Revenue",
        "type":"chart",
        "chart_type":"line",
        "x":"Month",
        "y":"Revenue"
    }},
    {{
        "id":"component_2",
        "title":"Top Customers",
        "type":"table"
    }},
    {{
        "id":"component_3",
        "title":"Total Revenue",
        "type":"kpi"
    }}
]
"""

    response = model.invoke(prompt)

    return parser.parse(response.content)