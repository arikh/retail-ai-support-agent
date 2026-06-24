"""
Embedding model wrapper using HuggingFace sentence-transformers.
Free, runs locally, no API key needed.
"""

import logging
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Model selected: lightweight, fast, good semantic quality
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load and return the HuggingFace embedding model.
    Downloads on first run (~90MB), cached locally after that.
    """
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )