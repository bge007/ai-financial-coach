from app.rag.store import DocumentStore, RetrievedChunk, get_store


def retrieve(user_id: int, query: str, k: int = 6) -> list[RetrievedChunk]:
    """Retrieve top-k chunks for a user with citation metadata."""
    return get_store().search(user_id=user_id, query=query, k=k)
