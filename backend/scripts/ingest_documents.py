"""
Ingest all documents from knowledge_base/raw/ into the vector store.

Usage:
    make ingest
    # or directly:
    PYTHONPATH=backend/src python backend/scripts/ingest_documents.py
"""

import logging
import sys
import time
from pathlib import Path

# ── Make sure examiner_coach is importable ────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.config import settings
from examiner_coach.db.vector_store import get_collection_stats
from examiner_coach.services.document_manager import add_document, load_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}

# Seconds to wait between files — respects Kisski rate limits
DELAY_BETWEEN_FILES = 3


def main() -> None:
    raw_dir = settings.knowledge_base_dir

    if not raw_dir.exists():
        logger.error(f"Knowledge base directory not found: {raw_dir}")
        sys.exit(1)

    # Collect all supported files
    files = [
        f for f in raw_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        logger.warning(f"No supported files found in {raw_dir}")
        sys.exit(0)

    logger.info(f"Found {len(files)} file(s) to process")
    logger.info(f"Already indexed: {load_registry()['indexed_files']}")

    # Process each file
    total_chunks = 0
    failed = []

    for i, file_path in enumerate(sorted(files)):
        try:
            chunks_added = add_document(file_path)
            total_chunks += chunks_added
        except Exception as e:
            logger.error(f"Failed to process '{file_path.name}': {e}")
            failed.append(file_path.name)

        # Respect rate limits — wait between every file except the last
        if i < len(files) - 1:
            logger.info(f"Waiting {DELAY_BETWEEN_FILES}s before next file...")
            time.sleep(DELAY_BETWEEN_FILES)

    # Summary
    stats = get_collection_stats()
    logger.info("─" * 50)
    logger.info(f"Done. Chunks added this run : {total_chunks}")
    logger.info(f"Total chunks in vector DB   : {stats['total_chunks']}")
    logger.info(f"Failed files                : {failed or 'none'}")


if __name__ == "__main__":
    main()