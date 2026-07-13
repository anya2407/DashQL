import chromadb
from langchain_openai import OpenAIEmbeddings
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Setup (runs once, at import)
# -----------------------------

_embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

_chroma_client = chromadb.PersistentClient(path="vector_store/")
_collection = _chroma_client.get_or_create_collection(
    name="dashboards",
    metadata={"hnsw:space": "cosine"}
)

# -----------------------------
# Similarity thresholds
# -----------------------------

SIMILARITY_THRESHOLD_EXACT = 0.90
SIMILARITY_THRESHOLD_SIMILAR = 0.60


def search_dashboard(query: str) -> Optional[str]:
    """
    Searches Chroma for an existing dashboard matching the query.
    """

    if _collection.count() == 0:
        return None

    query_embedding = _embedding_model.embed_query(query)

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=1
    )

    if not results["ids"] or not results["ids"][0]:
        return None

    distance = results["distances"][0][0]
    similarity = 1 - distance

    dashboard_id = results["metadatas"][0][0]["dashboard_id"]

    print(f"Query: '{query}' | Similarity: {similarity:.4f}")

    if similarity >= SIMILARITY_THRESHOLD_SIMILAR:
        return dashboard_id

    return None


def index_dashboard(dashboard_id: str, request_text: str) -> None:
    """
    Adds a newly generated dashboard's request text to Chroma.
    """

    embedding = _embedding_model.embed_query(request_text)

    _collection.add(
        ids=[dashboard_id],
        embeddings=[embedding],
        metadatas=[{"dashboard_id": dashboard_id, "request": request_text}]
    )