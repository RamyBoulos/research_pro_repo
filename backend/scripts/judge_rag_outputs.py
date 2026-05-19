"""
Judge saved RAG comparison outputs with a separate model and persist the
judgments for later review.

Usage:
    PYTHONPATH=backend/src python backend/scripts/judge_rag_outputs.py debug/rag_eval_results/compare_....json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.config import settings
from examiner_coach.services.document_manager import get_kisski_client
from examiner_coach.services.judge_prompt import build_judge_messages, judge_json_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def load_benchmark_index(benchmark_path: Path | None) -> dict[str, dict]:
    if benchmark_path is None or not benchmark_path.exists():
        return {}
    try:
        items = json.loads(benchmark_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to load benchmark file for judge calibration: %s", benchmark_path)
        return {}
    return {item["id"]: item for item in items if isinstance(item, dict) and item.get("id")}


def parse_judge_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            cleaned = "\n".join(lines[1:-1]).strip()
        else:
            cleaned = "\n".join(lines[1:]).strip()
    return json.loads(cleaned)


def judge_variant_output(entry: dict) -> dict:
    messages = build_judge_messages(
        transcript_id=entry["transcript_id"],
        transcript_language=entry["language"],
        transcript=entry["transcript"],
        variant_name=entry["variant_output"]["variant_name"],
        quality_band=entry.get("quality_band"),
        benchmark_notes=entry.get("notes"),
        gold_expected=entry.get("gold_expected"),
        retrieval_config=entry["variant_output"]["retrieval_config"],
        rag_context_results=entry["variant_output"]["rag_context"]["results"],
        generated_evaluation=entry["variant_output"]["result"],
    )
    client = get_kisski_client()
    response = client.chat.completions.create(
        model=settings.kisski_judge_model,
        messages=messages,
        temperature=0.0,
        max_tokens=1500,
    )
    raw_output = (response.choices[0].message.content or "").strip()
    return {
        "judge_model": settings.kisski_judge_model,
        "judge_schema": judge_json_schema(),
        "judge_messages": messages,
        "judge_raw_output": raw_output,
        "judge_result": parse_judge_json(raw_output),
    }


def compute_summary(judgments: list[dict]) -> dict:
    variant_aggregates: dict[str, dict[str, list[float]]] = {}
    for item in judgments:
        variant_name = item["variant_name"]
        scores = item["judge"]["judge_result"]["scores"]
        bucket = variant_aggregates.setdefault(variant_name, {})
        for key, value in scores.items():
            bucket.setdefault(key, []).append(float(value))

    summary: dict[str, dict[str, float]] = {}
    for variant_name, score_map in variant_aggregates.items():
        summary[variant_name] = {
            metric: round(sum(values) / len(values), 2)
            for metric, values in score_map.items()
            if values
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("comparison_file", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    comparison_payload = json.loads(args.comparison_file.read_text(encoding="utf-8"))
    benchmark_path_str = comparison_payload.get("benchmark_path")
    benchmark_path = Path(benchmark_path_str) if benchmark_path_str else None
    benchmark_index = load_benchmark_index(benchmark_path)
    judged_items: list[dict] = []

    for transcript_record in comparison_payload["variants"]:
        benchmark_item = benchmark_index.get(transcript_record["transcript_id"], {})
        for variant_output in transcript_record["variant_outputs"]:
            logger.info(
                "Judging transcript=%s variant=%s",
                transcript_record["transcript_id"],
                variant_output["variant_name"],
            )
            judged_items.append(
                {
                    "transcript_id": transcript_record["transcript_id"],
                    "language": transcript_record["language"],
                    "transcript": transcript_record["transcript"],
                    "quality_band": transcript_record.get("quality_band") or benchmark_item.get("quality_band"),
                    "notes": transcript_record.get("notes") or benchmark_item.get("notes"),
                    "gold_expected": benchmark_item.get("gold_expected"),
                    "variant_name": variant_output["variant_name"],
                    "variant_output": variant_output,
                    "judge": judge_variant_output(
                        {
                            "transcript_id": transcript_record["transcript_id"],
                            "language": transcript_record["language"],
                            "transcript": transcript_record["transcript"],
                            "quality_band": transcript_record.get("quality_band") or benchmark_item.get("quality_band"),
                            "notes": transcript_record.get("notes") or benchmark_item.get("notes"),
                            "gold_expected": benchmark_item.get("gold_expected"),
                            "variant_output": variant_output,
                        }
                    ),
                }
            )

    output_path = args.output or args.comparison_file.with_name(
        args.comparison_file.stem.replace("compare_", "judged_") + ".json"
    )
    judged_payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_comparison_file": str(args.comparison_file),
        "benchmark_path": str(benchmark_path) if benchmark_path else None,
        "judge_model": settings.kisski_judge_model,
        "items": judged_items,
        "summary": compute_summary(judged_items),
    }
    output_path.write_text(json.dumps(judged_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved judged results to %s", output_path)


if __name__ == "__main__":
    main()
