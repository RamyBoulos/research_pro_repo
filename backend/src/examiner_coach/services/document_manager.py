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

LOW_VALUE_SECTION_PATTERNS = (
    "references",
    "literatur",
    "bibliography",
    "further reading",
    "appendix",
    "appendices",
)

GUIDANCE_SECTION_PATTERNS = (
    "tip",
    "tips",
    "feedback",
    "recommendation",
    "recommendations",
    "practical example",
    "practical examples",
    "rules",
    "guidance",
    "how to do it well",
    "allgemeines feedbackregeln",
)

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
    return [chunk["text"] for chunk in chunk_document(text)]


def _build_section_label(metadata: dict) -> str:
    parts = [str(metadata.get(key, "")).strip() for key in ("h1", "h2", "h3")]
    return " > ".join(part for part in parts if part)


def _infer_chunk_type(section_label: str, text: str) -> str:
    lowered_label = section_label.lower()
    lowered_text = text.lower()

    if any(pattern in lowered_label for pattern in LOW_VALUE_SECTION_PATTERNS):
        return "references"
    if lowered_text.startswith("## references") or lowered_text.startswith("## literatur"):
        return "references"
    if lowered_text.startswith("## abstract"):
        return "abstract"
    if lowered_text.startswith("## conclusions") or lowered_text.startswith("## conclusion"):
        return "conclusion"
    if any(pattern in lowered_label for pattern in GUIDANCE_SECTION_PATTERNS):
        return "guidance"
    if "doi:" in lowered_text and lowered_text.count("\n- ") >= 2:
        return "references"
    return "content"


def _is_low_value_chunk(text: str, chunk_type: str) -> bool:
    lowered = text.lower()

    if chunk_type == "references":
        return True

    citation_markers = lowered.count("doi:") + lowered.count(" et al.")
    bullet_markers = lowered.count("\n- ")
    if citation_markers >= 2:
        return True
    if bullet_markers >= 4 and "recommend" not in lowered and "feedback" not in lowered:
        return True

    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if non_empty_lines:
        short_lines = sum(1 for line in non_empty_lines if len(line) < 120)
        if short_lines / len(non_empty_lines) > 0.8 and citation_markers >= 1:
            return True

    return False


def chunk_document(text: str) -> list[dict]:
    """
    Return chunk payloads with lightweight structural metadata so retrieval can
    prefer practical guidance over references and bibliography sections.
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

    final_chunks: list[dict] = []
    for doc in header_chunks:
        metadata = doc.metadata or {}
        section_label = _build_section_label(metadata)
        sub_chunks = char_splitter.split_text(doc.page_content)
        for sub_chunk in sub_chunks:
            cleaned_chunk = sub_chunk.strip()
            if len(cleaned_chunk) <= 100:
                continue

            chunk_type = _infer_chunk_type(section_label, cleaned_chunk)
            final_chunks.append(
                {
                    "text": cleaned_chunk,
                    "h1": metadata.get("h1"),
                    "h2": metadata.get("h2"),
                    "h3": metadata.get("h3"),
                    "section_label": section_label or None,
                    "chunk_type": chunk_type,
                    "is_low_value": _is_low_value_chunk(cleaned_chunk, chunk_type),
                }
            )

    return final_chunks


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
    chunk_payloads = chunk_document(text)
    if not chunk_payloads:
        logger.warning(f"No chunks generated from '{filename}'")
        return 0

    chunks = [payload["text"] for payload in chunk_payloads]
    logger.info(f"  → {len(chunks)} chunks")

    # 3. Embed
    embeddings = embed_chunks(chunks)
    logger.info(f"  → {len(embeddings)} embeddings")

    # 4. Store
    chunk_ids = [make_chunk_id(filename, i, c) for i, c in enumerate(chunks)]
    metadatas = [
        {
            "source": filename,
            "chunk_index": i,
            "h1": payload.get("h1"),
            "h2": payload.get("h2"),
            "h3": payload.get("h3"),
            "section_label": payload.get("section_label"),
            "chunk_type": payload.get("chunk_type", "content"),
            "is_low_value": bool(payload.get("is_low_value", False)),
        }
        for i, payload in enumerate(chunk_payloads)
    ]

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
