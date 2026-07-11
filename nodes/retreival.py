from typing import Optional


def search_dashboard(query: str) -> Optional[dict]:
    """
    Searches the vector database for an existing dashboard.

    Parameters
    ----------
    query : str
        User dashboard request.

    Returns
    -------
    dict
        Dashboard definition if a sufficiently similar
        dashboard exists.

    None
        If no dashboard passes the similarity threshold.
    """

    # TODO:
    # 1. Generate embedding
    # 2. Search FAISS
    # 3. If similarity >= threshold:
    #       load dashboard.json
    #       return dashboard
    # 4. else:
    #       return None

    return None