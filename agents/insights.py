from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


def generate_insights(request: str, components: list, datasets: dict) -> str:
    """
    Generates a short natural-language business insight summary
    based on the dashboard's computed data.

    Parameters
    ----------
    request : str
        Original user request.

    components : list
        Dashboard components (with titles/descriptions).

    datasets : dict
        Dict mapping component id -> list of row dicts (records).

    Returns
    -------
    str
        A short natural-language insights summary.
    """

    data_summary = []
    for component in components:
        rows = datasets.get(component["id"], [])
        preview = rows[:10]  # cap what we send to the model, keep prompt small
        data_summary.append({
            "title": component.get("title", ""),
            "sample_data": preview
        })

    prompt = f"""
You are a business analyst. The user asked for this dashboard:

"{request}"

Here is the data behind each component:

{data_summary}

Write a short business insights summary (3-5 sentences max) highlighting
the most important trends, standout numbers, or notable patterns in this data.

Rules:
- Be specific — reference actual numbers/names from the data where relevant.
- Do not mention SQL, queries, or technical details.
- Do not restate the dashboard title, just give insights.
- If the data doesn't support a clear insight, say so briefly rather than
  inventing one.
"""

    response = model.invoke(prompt)
    return response.content if isinstance(response.content, str) else str(response.content)