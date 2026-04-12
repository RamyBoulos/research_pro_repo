import hashlib
import json
import logging
from pathlib import Path

from openai import OpenAI

from examiner_coach.config import settings
from examiner_coach.db.vector_store import (
    delete_chunks_by_source,
    upsert_chunks,
)

logger = logging.getLogger(__name__)

# ── Kisski client ─────────────────────────────────────────────

def get_kisski_client() -> OpenAI:
    return OpenAI(
        api_key=settings.kisski_api_key,
        base_url=settings.kisski_base_url,
    )


# ── Registry helpers ──────────────────────────────────────────

def load_registry() -> dict:
    if not settings.registry_path.exists():
        return {"indexed_files": []}
    with open(settings.registry_path) as f:
        return json.load(f)


def save_registry(registry: dict) -> None:
    with open(settings.registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def is_indexed(filename: str) -> bool:
    registry = load_registry()
    return filename in registry["indexed_files"]


# ── Document parsing via Kisski Docling ───────────────────────

def parse_document(file_path: Path) -> str:
    """
    Send document to Kisski Docling API for parsing.
    Returns clean extracted text.
    Supports: PDF, DOCX and other formats.
    """
    import httpx

    url = f"{settings.kisski_base_url}/documents/convert"

    with open(file_path, "rb") as f:
        files = {"document": (file_path.name, f, "multipart/form-data")}
        headers = {"Authorization": f"Bearer {settings.kisski_api_key}"}
        response = httpx.post(url, files=files, headers=headers, timeout=120)
        response.raise_for_status()

    data = response.json()
    # Docling returns text in the 'markdown' or 'text' field
    return data.get("markdown") or data.get("text") or ""


# ── Chunking ──────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[str]:
    """
    Split text into overlapping chunks.
    Simple sliding window — good enough for our document sizes.
    chunk_size and chunk_overlap are in characters.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - chunk_overlap

    return chunks


# ── Embedding ─────────────────────────────────────────────────

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks using Kisski embedding API.
    Returns a list of embedding vectors.
    """
    client = get_kisski_client()
    response = client.embeddings.create(
        input=chunks,
        model=settings.kisski_embedding_model,
    )
    return [item.embedding for item in response.data]


# ── Chunk ID generation ───────────────────────────────────────

def make_chunk_id(filename: str, chunk_index: int, chunk_text: str) -> str:
    """
    Generate a stable unique ID for a chunk.
    Based on filename + index + content hash.
    """
    content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
    return f"{filename}__chunk{chunk_index}__{content_hash}"


# ── Main operations ───────────────────────────────────────────

def add_document(file_path: Path) -> int:
    """
    Full pipeline: parse → chunk → embed → store.
    Returns number of chunks indexed.
    Skips if document is already indexed.
    """
    filename = file_path.name

    if is_indexed(filename):
        logger.info(f"'{filename}' already indexed — skipping")
        return 0

    logger.info(f"Processing '{filename}'...")

    # 1. Parse
    text = parse_document(file_path)
    if not text.strip():
        logger.warning(f"No text extracted from '{filename}'")
        return 0

    # 2. Chunk
    chunks = chunk_text(text)
    if not chunks:
        logger.warning(f"No chunks generated from '{filename}'")
        return 0

    logger.info(f"  → {len(chunks)} chunks")

    # 3. Embed
    embeddings = embed_chunks(chunks)
    logger.info(f"  → {len(embeddings)} embeddings")

    # 4. Store
    chunk_ids = [make_chunk_id(filename, i, c) for i, c in enumerate(chunks)]
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

    upsert_chunks(
        chunk_ids=chunk_ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    # 5. Update registry
    registry = load_registry()
    if filename not in registry["indexed_files"]:
        registry["indexed_files"].append(filename)
    save_registry(registry)

    logger.info(f"  → '{filename}' indexed successfully")
    return len(chunks)


def remove_document(filename: str) -> None:
    """
    Remove a document from the vector store and registry.
    """
    delete_chunks_by_source(filename)

    registry = load_registry()
    if filename in registry["indexed_files"]:
        registry["indexed_files"].remove(filename)
    save_registry(registry)

    logger.info(f"'{filename}' removed from knowledge base")