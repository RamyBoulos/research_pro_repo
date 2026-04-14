"""
Reset the vector store and registry so documents can be re-indexed from scratch.

Usage:
    make reset-vectors
    # or directly:
    PYTHONPATH=backend/src python backend/scripts/reset_vector_store.py
"""

import json
import logging
import sys
from pathlib import Path

# ── Make sure examiner_coach is importable ────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.config import settings
from examiner_coach.db.vector_store import reset_vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def reset_registry() -> None:
    settings.registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.registry_path, "w", encoding="utf-8") as f:
        json.dump({"indexed_files": []}, f, indent=2)
        f.write("\n")
    logger.info(f"Reset registry: {settings.registry_path}")


def main() -> None:
    reset_vector_store()
    reset_registry()
    logger.info("Vector store reset complete. You can run `make ingest` now.")


if __name__ == "__main__":
    main()
