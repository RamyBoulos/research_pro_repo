"""
Run controlled RAG-technique comparisons on a fixed benchmark set and save the
full outputs for benchmark-based review.

Usage:
    PYTHONPATH=backend/src python backend/scripts/compare_rag_variants.py
    PYTHONPATH=backend/src python backend/scripts/compare_rag_variants.py --variant-set extended
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.config import settings
from examiner_coach.services.rag_pipeline import (
    RetrievalConfig,
    evaluate_transcript_with_details,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_BENCHMARK_PATH = ROOT_DIR / "backend/data/rag_eval_benchmark.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "debug/rag_eval_results"


def load_benchmark(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_variants(variant_set: str) -> list[tuple[str, RetrievalConfig]]:
    core = [
        (
            "no_rag",
            RetrievalConfig(
                retrieval_mode="none",
                candidate_pool_size=0,
                final_k=0,
                normalize_to_english=True,
            ),
        ),
        (
            "direct_k8",
            RetrievalConfig(
                retrieval_mode="direct",
                candidate_pool_size=20,
                final_k=8,
                normalize_to_english=True,
            ),
        ),
        (
            "direct_k8_unfiltered",
            RetrievalConfig(
                retrieval_mode="direct",
                candidate_pool_size=20,
                final_k=8,
                normalize_to_english=True,
                criterion_aware_query=False,
                enable_quality_reranking=False,
            ),
        ),
        (
            "hyde_k8",
            RetrievalConfig(
                retrieval_mode="hyde",
                candidate_pool_size=20,
                final_k=8,
                normalize_to_english=True,
            ),
        ),
        (
            "hyde_k8_unfiltered",
            RetrievalConfig(
                retrieval_mode="hyde",
                candidate_pool_size=20,
                final_k=8,
                normalize_to_english=True,
                criterion_aware_query=False,
                enable_quality_reranking=False,
            ),
        ),
    ]

    if variant_set == "core":
        return core

    return core + [
        (
            "direct_k4",
            RetrievalConfig(retrieval_mode="direct", candidate_pool_size=20, final_k=4),
        ),
        (
            "direct_k12",
            RetrievalConfig(retrieval_mode="direct", candidate_pool_size=20, final_k=12),
        ),
        (
            "hyde_k4",
            RetrievalConfig(retrieval_mode="hyde", candidate_pool_size=20, final_k=4),
        ),
        (
            "hyde_k12",
            RetrievalConfig(retrieval_mode="hyde", candidate_pool_size=20, final_k=12),
        ),
        (
            "direct_k8_no_translation",
            RetrievalConfig(
                retrieval_mode="direct",
                candidate_pool_size=20,
                final_k=8,
                normalize_to_english=False,
            ),
        ),
    ]


def to_jsonable_details(details: dict) -> dict:
    result = details["result"].model_dump(mode="json")
    return {
        "result": result,
        "normalized_transcript": details["normalized_transcript"],
        "rag_context": details["rag_context"],
        "raw_output": details["raw_output"],
        "messages": details["messages"],
        "retrieval_config": details["retrieval_config"],
    }


def compute_variant_summary(payload: dict) -> dict[str, dict]:
    summary: dict[str, dict] = {}

    variant_scores: dict[str, list[float]] = defaultdict(list)
    variant_criteria_met: dict[str, list[tuple[int, int]]] = defaultdict(list)
    variant_per_criterion: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for transcript_record in payload["variants"]:
        for variant_output in transcript_record["variant_outputs"]:
            name = variant_output["variant_name"]
            result = variant_output["result"]
            variant_scores[name].append(float(result["overall_score"]))
            variant_criteria_met[name].append((int(result["criteria_met"]), int(result["total_criteria"])))
            for criterion in result["criteria"]:
                variant_per_criterion[name][criterion["criterion_id"]].append(
                    float(criterion["score_percent"])
                )

    for variant_name, scores in variant_scores.items():
        criteria_pairs = variant_criteria_met[variant_name]
        total_criteria = criteria_pairs[0][1] if criteria_pairs else 0
        per_criterion = {
            criterion_id: round(sum(values) / len(values), 2)
            for criterion_id, values in variant_per_criterion[variant_name].items()
            if values
        }
        summary[variant_name] = {
            "avg_overall_score": round(sum(scores) / len(scores), 2),
            "min_overall_score": round(min(scores), 2),
            "max_overall_score": round(max(scores), 2),
            "avg_criteria_met": round(sum(met for met, _ in criteria_pairs) / len(criteria_pairs), 2),
            "total_criteria": total_criteria,
            "avg_per_criterion_score": per_criterion,
        }

    return summary


def compute_quality_band_summary(payload: dict) -> dict[str, dict[str, dict]]:
    grouped_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for transcript_record in payload["variants"]:
        band = transcript_record.get("quality_band", "unknown")
        for variant_output in transcript_record["variant_outputs"]:
            grouped_scores[band][variant_output["variant_name"]].append(
                float(variant_output["result"]["overall_score"])
            )

    summary: dict[str, dict[str, dict]] = {}
    for band, variant_map in grouped_scores.items():
        summary[band] = {}
        for variant_name, scores in variant_map.items():
            summary[band][variant_name] = {
                "avg_overall_score": round(sum(scores) / len(scores), 2),
                "scores": [round(score, 2) for score in scores],
            }
    return summary


def compute_gold_band_distance_summary(
    payload: dict,
    benchmark_items: list[dict],
) -> dict[str, dict]:
    benchmark_index = {item["id"]: item for item in benchmark_items}

    def distance_to_band(score: float, band: list[float]) -> float:
        lower, upper = float(band[0]), float(band[1])
        if lower <= score <= upper:
            return 0.0
        if score < lower:
            return lower - score
        return score - upper

    variant_distances: dict[str, list[float]] = defaultdict(list)
    quality_band_distances: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for transcript_record in payload["variants"]:
        item = benchmark_index[transcript_record["transcript_id"]]
        quality_band = item.get("quality_band", "unknown")
        target_band = item["gold_expected"]["overall_score_band"]

        for variant_output in transcript_record["variant_outputs"]:
            variant_name = variant_output["variant_name"]
            score = float(variant_output["result"]["overall_score"])
            distance = distance_to_band(score, target_band)
            variant_distances[variant_name].append(distance)
            quality_band_distances[quality_band][variant_name].append(distance)

    overall_summary = {
        variant_name: {
            "avg_distance_to_gold_band": round(sum(distances) / len(distances), 2),
            "max_distance_to_gold_band": round(max(distances), 2),
            "within_band_count": sum(1 for distance in distances if distance == 0.0),
            "total_cases": len(distances),
        }
        for variant_name, distances in variant_distances.items()
        if distances
    }

    by_quality_band: dict[str, dict[str, dict]] = {}
    for quality_band, variant_map in quality_band_distances.items():
        by_quality_band[quality_band] = {}
        for variant_name, distances in variant_map.items():
            by_quality_band[quality_band][variant_name] = {
                "avg_distance_to_gold_band": round(sum(distances) / len(distances), 2),
                "within_band_count": sum(1 for distance in distances if distance == 0.0),
                "total_cases": len(distances),
            }

    return {
        "overall": overall_summary,
        "by_quality_band": by_quality_band,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--variant-set", choices=["core", "extended"], default="core")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    benchmark_items = load_benchmark(args.benchmark)
    variants = build_variants(args.variant_set)

    run_started = datetime.now(timezone.utc)
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output or output_dir / f"compare_{run_started.strftime('%Y%m%dT%H%M%SZ')}.json"

    payload = {
        "run_started_at": run_started.isoformat(),
        "generator_model": settings.kisski_llm_model,
        "embedding_model": settings.kisski_embedding_model,
        "variant_set": args.variant_set,
        "benchmark_path": str(args.benchmark),
        "benchmark_size": len(benchmark_items),
        "variants": [],
    }

    for item in benchmark_items:
        logger.info("Running benchmark transcript: %s", item["id"])
        transcript_record = {
            "transcript_id": item["id"],
            "language": item["language"],
            "duration_seconds": item["duration_seconds"],
            "duration_bucket": item.get("duration_bucket"),
            "quality_band": item.get("quality_band"),
            "notes": item.get("notes"),
            "transcript": item["transcript"],
            "variant_outputs": [],
        }

        for variant_name, config in variants:
            logger.info("  variant=%s", variant_name)
            details = evaluate_transcript_with_details(
                transcript=item["transcript"],
                duration_seconds=float(item["duration_seconds"]),
                config=config,
            )
            transcript_record["variant_outputs"].append(
                {
                    "variant_name": variant_name,
                    **to_jsonable_details(details),
                }
            )

        payload["variants"].append(transcript_record)

    payload["variant_summary"] = compute_variant_summary(payload)
    payload["quality_band_summary"] = compute_quality_band_summary(payload)
    payload["gold_band_distance_summary"] = compute_gold_band_distance_summary(
        payload,
        benchmark_items=benchmark_items,
    )

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved comparison results to %s", output_path)


if __name__ == "__main__":
    main()
