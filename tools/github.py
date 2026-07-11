import os
import json
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # e.g. "yourusername/DashQL"

_github_client = Github(GITHUB_TOKEN)
_repo = _github_client.get_repo(GITHUB_REPO)


def save_dashboard_to_github(dashboard_id: str, dashboard_data: dict) -> bool:
    """
    Saves a dashboard's full data (layout, sql, metadata) as one
    combined JSON file to the GitHub repo, at dashboards/{dashboard_id}.json.

    Parameters
    ----------
    dashboard_id : str
        Unique identifier for this dashboard.

    dashboard_data : dict
        Combined dashboard content, expected shape:
        {
            "dashboard_id": str,
            "request": str,
            "dashboard_layout": list,
            "sql_queries": list,
            "timestamp": str
        }

    Returns
    -------
    bool
        True if saved successfully, False otherwise.
    """

    path = f"dashboards/{dashboard_id}.json"
    content = json.dumps(dashboard_data, indent=2)

    try:
        # Check if file already exists (needed to update vs create)
        existing_file = _repo.get_contents(path)
        _repo.update_file(
            path=path,
            message=f"Update dashboard {dashboard_id}",
            content=content,
            sha=existing_file.sha
        )
    except GithubException as e:
        if e.status == 404:
            # File doesn't exist yet — create it
            _repo.create_file(
                path=path,
                message=f"Create dashboard {dashboard_id}",
                content=content
            )
        else:
            print(f"GitHub save error: {e}")
            return False

    return True


def load_dashboard_from_github(dashboard_id: str) -> dict | None:
    """
    Loads a dashboard's combined JSON data from GitHub.

    Parameters
    ----------
    dashboard_id : str
        Unique identifier for the dashboard to load.

    Returns
    -------
    dict
        The dashboard's data if found.

    None
        If the dashboard doesn't exist or couldn't be loaded.
    """

    path = f"dashboards/{dashboard_id}.json"

    try:
        file_content = _repo.get_contents(path)
        decoded = file_content.decoded_content.decode("utf-8")
        return json.loads(decoded)
    except GithubException as e:
        if e.status == 404:
            return None
        print(f"GitHub load error: {e}")
        return None