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
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from examiner_coach.config import settings
from examiner_coach.services.document_manager import get_kisski_client
from examiner_coach.services.judge_prompt import build_judge_messages, judge_json_schema

try:
    from openai import RateLimitError
except Exception:  # pragma: no cover - keeps the script importable if SDK changes.
    RateLimitError = RuntimeError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def default_output_path(comparison_file: Path) -> Path:
    return comparison_file.with_name(
        comparison_file.stem.replace("compare_", "judged_") + ".json"
    )


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


def build_judged_payload(
    *,
    comparison_file: Path,
    benchmark_path: Path | None,
    judged_items: list[dict],
) -> dict:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_comparison_file": str(comparison_file),
        "benchmark_path": str(benchmark_path) if benchmark_path else None,
        "judge_model": settings.kisski_judge_model,
        "items": judged_items,
        "summary": compute_summary(judged_items),
    }


def save_judged_payload(
    *,
    output_path: Path,
    comparison_file: Path,
    benchmark_path: Path | None,
    judged_items: list[dict],
) -> None:
    payload = build_judged_payload(
        comparison_file=comparison_file,
        benchmark_path=benchmark_path,
        judged_items=judged_items,
    )
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_existing_items(output_path: Path) -> list[dict]:
    if not output_path.exists():
        return []
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not read existing judged output for resume: %s", output_path)
        return []
    items = payload.get("items", [])
    if not isinstance(items, list):
        return []
    return items


def item_key(item: dict) -> tuple[str | None, str | None]:
    return item.get("transcript_id"), item.get("variant_name")


def _distance_to_band(score: float, band: list[float]) -> float:
    lower, upper = float(band[0]), float(band[1])
    if lower <= score <= upper:
        return 0.0
    if score < lower:
        return lower - score
    return score - upper


def compute_band_diagnostics(generated_evaluation: dict, gold_expected: dict | None) -> dict:
    if not gold_expected:
        return {
            "has_gold_expected": False,
            "overall_distance_to_band": None,
            "criterion_distances_to_band": {},
            "criteria_inside_band": [],
            "criteria_outside_band": {},
        }

    overall_score = float(generated_evaluation.get("overall_score", 0))
    overall_band = gold_expected.get("overall_score_band")
    overall_distance = (
        _distance_to_band(overall_score, overall_band)
        if isinstance(overall_band, list) and len(overall_band) == 2
        else None
    )

    criteria_expected = gold_expected.get("criteria_expected") or {}
    generated_criteria = {
        item.get("criterion_id"): float(item.get("score_percent", 0))
        for item in generated_evaluation.get("criteria", [])
        if isinstance(item, dict) and item.get("criterion_id")
    }

    criterion_distances: dict[str, float] = {}
    criteria_inside: list[str] = []
    criteria_outside: dict[str, dict] = {}
    for criterion_id, band in criteria_expected.items():
        if not isinstance(band, list) or len(band) != 2 or criterion_id not in generated_criteria:
            continue
        score = generated_criteria[criterion_id]
        distance = _distance_to_band(score, band)
        criterion_distances[criterion_id] = distance
        if distance == 0.0:
            criteria_inside.append(criterion_id)
        else:
            direction = "too_low" if score < float(band[0]) else "too_high"
            criteria_outside[criterion_id] = {
                "generated_score": score,
                "gold_band": band,
                "distance": distance,
                "direction": direction,
            }

    return {
        "has_gold_expected": True,
        "overall_score": overall_score,
        "overall_gold_band": overall_band,
        "overall_distance_to_band": overall_distance,
        "criterion_distances_to_band": criterion_distances,
        "criteria_inside_band": criteria_inside,
        "criteria_outside_band": criteria_outside,
    }


def _response_metadata(response) -> dict:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if hasattr(response, "dict"):
        return response.dict()
    return {"repr": repr(response)}


def judge_variant_output(
    entry: dict,
    *,
    max_retries: int = 2,
    rate_limit_retries: int = 6,
    rate_limit_sleep: float = 30.0,
) -> dict:
    generated_evaluation = entry["variant_output"]["result"]
    gold_expected = entry.get("gold_expected")
    messages = build_judge_messages(
        transcript_id=entry["transcript_id"],
        transcript_language=entry["language"],
        transcript=entry["transcript"],
        variant_name=entry["variant_output"]["variant_name"],
        quality_band=entry.get("quality_band"),
        benchmark_notes=entry.get("notes"),
        gold_expected=gold_expected,
        retrieval_config=entry["variant_output"]["retrieval_config"],
        rag_context_results=entry["variant_output"]["rag_context"]["results"],
        generated_evaluation=generated_evaluation,
    )
    client = get_kisski_client()
    attempts: list[dict] = []
    judge_result = None
    parse_error = None
    raw_output = ""

    attempt_index = 0
    rate_limit_attempt = 0
    while attempt_index <= max_retries:
        try:
            response = client.chat.completions.create(
                model=settings.kisski_judge_model,
                messages=messages,
                temperature=0.0,
                max_tokens=1800,
            )
        except RateLimitError as exc:
            rate_limit_attempt += 1
            if rate_limit_attempt > rate_limit_retries:
                raise
            sleep_seconds = rate_limit_sleep * rate_limit_attempt
            logger.warning(
                "Rate limited for transcript=%s variant=%s. Sleeping %.1fs before retry %d/%d.",
                entry["transcript_id"],
                entry["variant_output"]["variant_name"],
                sleep_seconds,
                rate_limit_attempt,
                rate_limit_retries,
            )
            time.sleep(sleep_seconds)
            continue

        raw_output = (response.choices[0].message.content or "").strip()
        metadata = _response_metadata(response)
        try:
            judge_result = parse_judge_json(raw_output)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
            attempts.append(
                {
                    "attempt": attempt_index + 1,
                    "raw_output": raw_output,
                    "parse_error": parse_error,
                    "response_metadata": metadata,
                }
            )
            logger.error(
                "Judge returned invalid JSON for transcript=%s variant=%s attempt=%d/%d. Raw preview=%r",
                entry["transcript_id"],
                entry["variant_output"]["variant_name"],
                attempt_index + 1,
                max_retries + 1,
                raw_output[:500],
            )
            if attempt_index < max_retries:
                time.sleep(2 * (attempt_index + 1))
                attempt_index += 1
                continue
        else:
            parse_error = None
            attempts.append(
                {
                    "attempt": attempt_index + 1,
                    "raw_output": raw_output,
                    "parse_error": None,
                    "response_metadata": metadata,
                }
            )
        break

    return {
        "judge_model": settings.kisski_judge_model,
        "judge_schema": judge_json_schema(),
        "band_diagnostics": compute_band_diagnostics(generated_evaluation, gold_expected),
        "judge_messages": messages,
        "judge_raw_output": raw_output,
        "judge_result": judge_result,
        "judge_parse_error": parse_error,
        "judge_attempts": attempts,
    }


def compute_summary(judgments: list[dict]) -> dict:
    variant_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    variant_band_distances: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for item in judgments:
        variant_name = item["variant_name"]
        judge_result = item["judge"].get("judge_result")
        if not isinstance(judge_result, dict):
            continue
        scores = judge_result.get("scores", {})
        for key, value in scores.items():
            variant_scores[variant_name][key].append(float(value))

        diagnostics = item["judge"]["band_diagnostics"]
        overall_distance = diagnostics.get("overall_distance_to_band")
        if overall_distance is not None:
            variant_band_distances[variant_name]["overall_distance_to_band"].append(float(overall_distance))
        for distance in diagnostics.get("criterion_distances_to_band", {}).values():
            variant_band_distances[variant_name]["criterion_distance_to_band"].append(float(distance))

    summary: dict[str, dict] = {}
    for variant_name, score_map in variant_scores.items():
        judge_scores = {
            metric: round(sum(values) / len(values), 2)
            for metric, values in score_map.items()
            if values
        }
        calibration_metrics = [
            judge_scores.get("overall_band_fit"),
            judge_scores.get("criterion_band_fit"),
            judge_scores.get("benchmark_expectation_match"),
            judge_scores.get("directional_correctness"),
        ]
        calibration_metrics = [value for value in calibration_metrics if value is not None]

        summary[variant_name] = {
            "judge_scores": {
                **judge_scores,
                "mean_calibration_judgment": (
                    round(sum(calibration_metrics) / len(calibration_metrics), 2)
                    if calibration_metrics
                    else None
                ),
            },
            "band_distances": {
                metric: round(sum(values) / len(values), 2)
                for metric, values in variant_band_distances[variant_name].items()
                if values
            },
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("comparison_file", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--save-every",
        type=int,
        default=1,
        help="Persist progress after this many judged items.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retry a judge call when the response is empty or invalid JSON.",
    )
    parser.add_argument(
        "--rate-limit-retries",
        type=int,
        default=6,
        help="Retry this many times after API 429 rate-limit errors.",
    )
    parser.add_argument(
        "--rate-limit-sleep",
        type=float,
        default=30.0,
        help="Base seconds for linear backoff after 429 errors.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing judged output file and skip completed items.",
    )
    args = parser.parse_args()

    comparison_payload = json.loads(args.comparison_file.read_text(encoding="utf-8"))
    benchmark_path_str = comparison_payload.get("benchmark_path")
    benchmark_path = Path(benchmark_path_str) if benchmark_path_str else None
    benchmark_index = load_benchmark_index(benchmark_path)
    output_path = args.output or default_output_path(args.comparison_file)
    judged_items: list[dict] = load_existing_items(output_path) if args.resume else []
    completed_keys = {item_key(item) for item in judged_items}
    if judged_items:
        logger.info("Loaded %d existing judged items from %s", len(judged_items), output_path)

    for transcript_record in comparison_payload["variants"]:
        benchmark_item = benchmark_index.get(transcript_record["transcript_id"], {})
        for variant_output in transcript_record["variant_outputs"]:
            logger.info(
                "Judging transcript=%s variant=%s",
                transcript_record["transcript_id"],
                variant_output["variant_name"],
            )
            entry = {
                "transcript_id": transcript_record["transcript_id"],
                "language": transcript_record["language"],
                "transcript": transcript_record["transcript"],
                "quality_band": transcript_record.get("quality_band") or benchmark_item.get("quality_band"),
                "notes": transcript_record.get("notes") or benchmark_item.get("notes"),
                "gold_expected": benchmark_item.get("gold_expected"),
                "variant_output": variant_output,
            }
            key = (entry["transcript_id"], variant_output["variant_name"])
            if key in completed_keys:
                logger.info(
                    "Skipping already judged transcript=%s variant=%s",
                    key[0],
                    key[1],
                )
                continue
            judged_items.append(
                {
                    **entry,
                    "variant_name": variant_output["variant_name"],
                    "judge": judge_variant_output(
                        entry,
                        max_retries=args.max_retries,
                        rate_limit_retries=args.rate_limit_retries,
                        rate_limit_sleep=args.rate_limit_sleep,
                    ),
                }
            )
            completed_keys.add(key)
            if args.save_every > 0 and len(judged_items) % args.save_every == 0:
                save_judged_payload(
                    output_path=output_path,
                    comparison_file=args.comparison_file,
                    benchmark_path=benchmark_path,
                    judged_items=judged_items,
                )

    save_judged_payload(
        output_path=output_path,
        comparison_file=args.comparison_file,
        benchmark_path=benchmark_path,
        judged_items=judged_items,
    )
    logger.info("Saved judged results to %s", output_path)


if __name__ == "__main__":
    main()
