"""
Run a single transcript through the evaluation pipeline with a chosen retrieval
mode and save the detailed output locally for inspection.

Usage:
    PYTHONPATH=backend/src python backend/scripts/evaluate_sample.py --transcript-id en_weak_comm_short_01
    PYTHONPATH=backend/src python backend/scripts/evaluate_sample.py --transcript "Your transcript here" --duration 45 --mode none
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.services.rag_pipeline import RetrievalConfig, evaluate_transcript_with_details

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_BENCHMARK_PATH = ROOT_DIR / "backend/data/rag_eval_benchmark.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "debug/rag_eval_results"


def load_benchmark_item(benchmark_path: Path, transcript_id: str) -> dict:
    items = json.loads(benchmark_path.read_text(encoding="utf-8"))
    for item in items:
        if item["id"] == transcript_id:
            return item
    raise ValueError(f"Transcript id not found in benchmark: {transcript_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--transcript-id", type=str, default="en_weak_comm_short_01")
    parser.add_argument("--transcript", type=str, default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--mode", choices=["none", "direct", "hyde"], default="direct")
    parser.add_argument("--final-k", type=int, default=8)
    parser.add_argument("--candidate-pool-size", type=int, default=20)
    parser.add_argument("--no-translation", action="store_true")
    parser.add_argument("--no-criterion-aware-query", action="store_true")
    parser.add_argument("--no-quality-reranking", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.transcript is None:
        item = load_benchmark_item(args.benchmark, args.transcript_id)
        transcript = item["transcript"]
        duration_seconds = float(item["duration_seconds"])
        transcript_id = item["id"]
    else:
        transcript = args.transcript
        duration_seconds = float(args.duration or 0.0)
        transcript_id = "manual_input"

    config = RetrievalConfig(
        retrieval_mode=args.mode,
        candidate_pool_size=0 if args.mode == "none" else args.candidate_pool_size,
        final_k=0 if args.mode == "none" else args.final_k,
        normalize_to_english=not args.no_translation,
        criterion_aware_query=not args.no_criterion_aware_query,
        enable_quality_reranking=not args.no_quality_reranking,
    )
    details = evaluate_transcript_with_details(
        transcript=transcript,
        duration_seconds=duration_seconds,
        config=config,
    )

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transcript_id": transcript_id,
        "config": details["retrieval_config"],
        "normalized_transcript": details["normalized_transcript"],
        "rag_context": details["rag_context"],
        "result": details["result"].model_dump(mode="json"),
        "raw_output": details["raw_output"],
    }

    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output or output_dir / f"sample_{transcript_id}_{args.mode}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved sample evaluation to %s", output_path)


if __name__ == "__main__":
    main()
