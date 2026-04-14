import hashlib
import json
import logging
import re
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
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


def clean_parsed_text(text: str) -> str:
    """
    Remove obvious parser artifacts while preserving nearby semantic content.
    This intentionally keeps surrounding paragraphs in case OCR extracted
    useful captions or figure text.
    """
    cleaned_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        if re.fullmatch(r"picture-\d+\.(png|jpg|jpeg)", stripped, flags=re.IGNORECASE):
            continue

        if re.fullmatch(r"https?://\S+", stripped, flags=re.IGNORECASE):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# ── Chunking ──────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """
    Context-aware chunking for Docling markdown output.
    Step 1: Split on markdown headers to respect document structure.
    Step 2: Further split large sections on paragraphs/sentences.
    """
    # Step 1 — split on document structure
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )
    header_chunks = header_splitter.split_text(text)

    # Step 2 — further split large sections
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=120,
        separators=["\n\n", "\n", " ", ""],
    )

    final_chunks = []
    for doc in header_chunks:
        sub_chunks = char_splitter.split_text(doc.page_content)
        final_chunks.extend(sub_chunks)

    return [c for c in final_chunks if len(c.strip()) > 100]


# ── Embedding ─────────────────────────────────────────────────

def format_passage_for_embedding(text: str) -> str:
    """
    Format stored document text for E5-style retrieval models.
    """
    return f"passage: {text.strip()}"


def format_query_for_embedding(text: str) -> str:
    """
    Format user queries for E5-style retrieval models.
    """
    return f"query: {text.strip()}"


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks using Kisski embedding API.
    Returns a list of embedding vectors.
    """
    client = get_kisski_client()
    formatted_chunks = [format_passage_for_embedding(chunk) for chunk in chunks]
    response = client.embeddings.create(
        input=formatted_chunks,
        model=settings.kisski_embedding_model,
    )
    return [item.embedding for item in response.data]


def embed_query(query: str) -> list[float]:
    """
    Embed a user query using the same retrieval convention as stored passages.
    """
    client = get_kisski_client()
    response = client.embeddings.create(
        input=[format_query_for_embedding(query)],
        model=settings.kisski_embedding_model,
    )
    return response.data[0].embedding


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
    text = clean_parsed_text(parse_document(file_path))
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
