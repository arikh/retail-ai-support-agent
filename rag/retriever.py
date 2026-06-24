"""
Retriever — semantic search against ChromaDB knowledge base.
Returns relevant chunks for a given query.
"""

import logging
from langchain_chroma import Chroma
from langchain_core.documents import Document
from rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = "chroma_db"
TOP_K          = 3


def get_vectorstore() -> Chroma:
    """Load existing ChromaDB vectorstore."""
    embedding_model = get_embedding_model()
    return Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embedding_model,
    )


def retrieve(query: str, k: int = TOP_K) -> list[Document]:
    """
    Retrieve top-k relevant chunks for a query.
    Returns list of LangChain Document objects.
    """
    logger.info(f"Retrieving chunks for query: {query}")
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(query, k=k)
    logger.info(f"Retrieved {len(results)} chunks")
    return results


def retrieve_as_text(query: str, k: int = TOP_K) -> str:
    """
    Retrieve and format chunks as a single text string.
    Used for injecting context into agent prompts.
    """
    docs = retrieve(query, k=k)
    if not docs:
        return "No relevant information found in knowledge base."

    context = "\n\n---\n\n".join([doc.page_content for doc in docs])
    return context


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    test_queries = [
        "Why was a material excluded due to expiry?",
        "What does downstream failed mean?",
        "How do I fix a market mapping issue?",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        result = retrieve_as_text(query)
        print(result[:300])