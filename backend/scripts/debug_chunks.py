"""
Debug document parsing and chunking for a single source file.

Usage:
    PYTHONPATH=backend/src python backend/scripts/debug_chunks.py "Hattie and Timperley_2007.pdf"
"""

import json
import logging
import statistics
import sys
from pathlib import Path

# Make sure examiner_coach is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.config import settings
from examiner_coach.services.document_manager import (
    chunk_text,
    clean_parsed_text,
    parse_document,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def sanitize_stem(filename: str) -> str:
    return Path(filename).stem.replace(" ", "_")


def main() -> None:
    if len(sys.argv) != 2:
        logger.error('Usage: python backend/scripts/debug_chunks.py "<filename>"')
        sys.exit(1)

    filename = sys.argv[1]
    file_path = settings.knowledge_base_dir / filename

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    logger.info(f"Parsing: {file_path.name}")
    parsed_text = clean_parsed_text(parse_document(file_path))

    if not parsed_text.strip():
        logger.error("No text extracted from document")
        sys.exit(1)

    chunks = chunk_text(parsed_text)
    chunk_lengths = [len(chunk) for chunk in chunks]

    output_dir = Path("debug/chunks") / sanitize_stem(filename)
    output_dir.mkdir(parents=True, exist_ok=True)

    parsed_text_path = output_dir / "parsed_text.txt"
    chunks_json_path = output_dir / "chunks.json"
    chunks_txt_path = output_dir / "chunks.txt"

    parsed_text_path.write_text(parsed_text, encoding="utf-8")

    chunks_payload = [
        {
            "chunk_index": i,
            "length": len(chunk),
            "text": chunk,
        }
        for i, chunk in enumerate(chunks)
    ]
    chunks_json_path.write_text(
        json.dumps(
            {
                "source_file": filename,
                "parsed_text_length": len(parsed_text),
                "chunk_count": len(chunks),
                "min_chunk_length": min(chunk_lengths) if chunk_lengths else 0,
                "max_chunk_length": max(chunk_lengths) if chunk_lengths else 0,
                "avg_chunk_length": round(statistics.mean(chunk_lengths), 2)
                if chunk_lengths
                else 0,
                "chunks": chunks_payload,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with chunks_txt_path.open("w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            f.write(f"=== Chunk {i} | length={len(chunk)} ===\n")
            f.write(chunk)
            f.write("\n\n")

    logger.info(f"Parsed text length : {len(parsed_text)}")
    logger.info(f"Chunk count        : {len(chunks)}")
    if chunk_lengths:
        logger.info(f"Min chunk length   : {min(chunk_lengths)}")
        logger.info(f"Max chunk length   : {max(chunk_lengths)}")
        logger.info(f"Avg chunk length   : {round(statistics.mean(chunk_lengths), 2)}")
    logger.info(f"Saved parsed text  : {parsed_text_path}")
    logger.info(f"Saved chunks JSON  : {chunks_json_path}")
    logger.info(f"Saved chunks TXT   : {chunks_txt_path}")


if __name__ == "__main__":
    main()
