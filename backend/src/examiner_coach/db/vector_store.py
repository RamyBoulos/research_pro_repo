import logging
from pathlib import Path
import shutil

import chromadb
from chromadb.config import Settings as ChromaSettings

from examiner_coach.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "examiner_coach_knowledge"


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Returns a persistent ChromaDB client.
    Data is stored in knowledge_base/processed/ and survives restarts.
    """
    db_path = settings.vector_db_dir
    db_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client


def get_collection() -> chromadb.Collection:
    """
    Returns the knowledge base collection.
    Creates it if it does not exist yet.
    """
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def upsert_chunks(
    chunk_ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """
    Insert or update chunks in the collection.
    Called by document_manager after embedding.
    """
    collection = get_collection()
    collection.upsert(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.info(f"Upserted {len(chunk_ids)} chunks into ChromaDB")


def query_collection(
    query_embedding: list[float],
    n_results: int = 10,
) -> list[dict]:
    """
    Query the collection with an embedding vector.
    Returns top n_results chunks with text and relevance score.
    """
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "distances", "metadatas"],
    )

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    return [
        {
            "text": doc,
            "source": meta.get("source", "unknown"),
            "relevance": round(1 - dist, 4),  # cosine distance → similarity
        }
        for doc, dist, meta in zip(documents, distances, metadatas)
    ]


def delete_chunks_by_source(filename: str) -> None:
    """
    Delete all chunks that came from a specific source file.
    Called when a document is removed from the knowledge base.
    """
    collection = get_collection()
    results = collection.get(
        where={"source": filename},
        include=["documents"],
    )
    ids_to_delete = results.get("ids", [])
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        logger.info(f"Deleted {len(ids_to_delete)} chunks for '{filename}'")
    else:
        logger.warning(f"No chunks found for '{filename}'")


def get_collection_stats() -> dict:
    """
    Returns basic stats about the collection.
    Useful for debugging and the /health endpoint later.
    """
    collection = get_collection()
    return {
        "collection": COLLECTION_NAME,
        "total_chunks": collection.count(),
    }


def reset_vector_store() -> None:
    """
    Remove the current Chroma collection data from disk.
    Use this before re-indexing when the embedding format changes.
    """
    db_path = settings.vector_db_dir
    if db_path.exists():
        shutil.rmtree(db_path)
        logger.info(f"Removed vector store directory: {db_path}")
    else:
        logger.info(f"Vector store directory does not exist: {db_path}")
