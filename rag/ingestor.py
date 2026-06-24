"""
Document ingestor — loads FAQ markdown files,
chunks them, embeds them, stores in ChromaDB.
Run once to build the knowledge base.
"""

import os
import logging
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

FAQ_DIR        = "data/faqs"
CHROMA_DB_PATH = "chroma_db"


def ingest_documents() -> int:
    """
    Load FAQ markdown files, chunk them, embed and store in ChromaDB.
    Returns number of chunks stored.
    """
    logger.info(f"Loading documents from {FAQ_DIR}")

    # Load all markdown files
    loader = DirectoryLoader(
        FAQ_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    logger.info(f"Loaded {len(documents)} documents")

    # Chunk documents
    # Fixed size with overlap — FAQ docs are semi-structured free text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"Split into {len(chunks)} chunks")

    # Embed and store in ChromaDB
    embedding_model = get_embedding_model()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=CHROMA_DB_PATH,
    )

    logger.info(
        f"Stored {len(chunks)} chunks in ChromaDB at {CHROMA_DB_PATH}"
    )
    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = ingest_documents()
    print(f"\n✓ Ingestion complete — {count} chunks stored in ChromaDB")