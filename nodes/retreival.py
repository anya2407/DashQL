import chromadb
from sentence_transformers import SentenceTransformer
from typing import Optional

# -----------------------------
# Setup (runs once, at import)
# -----------------------------

_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

_chroma_client = chromadb.PersistentClient(path="vector_store/")
_collection = _chroma_client.get_or_create_collection(name="dashboards")

# -----------------------------
# Similarity thresholds
# -----------------------------

SIMILARITY_THRESHOLD_EXACT = 0.95
SIMILARITY_THRESHOLD_SIMILAR = 0.60


def search_dashboard(query: str) -> Optional[str]:
    """
    Searches Chroma for an existing dashboard matching the query.

    Parameters
    ----------
    query : str
        User's dashboard request.

    Returns
    -------
    str
        dashboard_id if a sufficiently similar dashboard exists.

    None
        If no dashboard passes the similarity threshold.
    """

    # If the collection is empty, there's nothing to match against
    if _collection.count() == 0:
        return None

    query_embedding = _embedding_model.encode(query).tolist()

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=1
    )

    if not results["ids"] or not results["ids"][0]:
        return None

    # Chroma returns distance (lower = more similar), not similarity directly.
    # For cosine distance: similarity = 1 - distance
    distance = results["distances"][0][0]
    similarity = 1 - distance

    dashboard_id = results["metadatas"][0][0]["dashboard_id"]


    if similarity >= SIMILARITY_THRESHOLD_SIMILAR:
        return dashboard_id

    return None


def index_dashboard(dashboard_id: str, request_text: str) -> None:
    """
    Adds a newly generated dashboard's request text to Chroma,
    so future similar requests can find and reuse it.

    Parameters
    ----------
    dashboard_id : str
        Unique identifier for this dashboard (matches the GitHub filename).

    request_text : str
        The original user request that generated this dashboard.
    """

    embedding = _embedding_model.encode(request_text).tolist()

    _collection.add(
        ids=[dashboard_id],
        embeddings=[embedding],
        metadatas=[{"dashboard_id": dashboard_id, "request": request_text}]
    )