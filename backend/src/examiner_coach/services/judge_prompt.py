"""
Prompt builders for narrow LLM-as-judge checks over RAG comparison outputs.

The judge reads an already-generated evaluation and decides whether it matches
the benchmark gold expectations. The goal is to confirm or question the
direction suggested by the deterministic RAG-variant comparison.
"""

from __future__ import annotations

import json


JUDGE_RUBRIC = [
    "overall_band_fit",
    "criterion_band_fit",
    "benchmark_expectation_match",
    "directional_correctness",
]


def judge_json_schema() -> str:
    return """{
  "scores": {
    "overall_band_fit": "<integer 0-100, higher is better>",
    "criterion_band_fit": "<integer 0-100, higher is better>",
    "benchmark_expectation_match": "<integer 0-100, higher is better>",
    "directional_correctness": "<integer 0-100, higher is better>"
  },
  "band_assessment": {
    "overall_score_in_gold_band": "<boolean>",
    "criteria_in_gold_band": ["<criterion_id>"],
    "criteria_outside_gold_band": {
      "<criterion_id>": {
        "generated_score": "<number>",
        "gold_band": ["<lower>", "<upper>"],
        "direction": "<too_low|too_high>"
      }
    }
  },
  "forbidden_claim_violation": "<boolean>",
  "missing_gold_expectations": [
    "<short item from the gold expectations that the generated evaluation missed>"
  ],
  "verdict": "<1-3 sentences explaining whether this generated evaluation matches the benchmark expectations>"
}"""


def build_judge_messages(
    *,
    transcript_id: str,
    transcript_language: str,
    transcript: str,
    variant_name: str,
    quality_band: str | None,
    benchmark_notes: str | None,
    gold_expected: dict | None,
    retrieval_config: dict,
    rag_context_results: list[dict],
    generated_evaluation: dict,
) -> list[dict[str, str]]:
    """
    Build a strict judge prompt for a single generated evaluation.
    """
    evidence_block = (
        json.dumps(rag_context_results, ensure_ascii=False, indent=2)
        if rag_context_results
        else "[]"
    )
    evaluation_block = json.dumps(generated_evaluation, ensure_ascii=False, indent=2)
    retrieval_block = json.dumps(retrieval_config, ensure_ascii=False, indent=2)
    gold_block = (
        json.dumps(gold_expected, ensure_ascii=False, indent=2)
        if gold_expected
        else "null"
    )
    benchmark_notes_block = benchmark_notes or "None provided."
    quality_band_block = quality_band or "unknown"

    system_prompt = (
        "You are a narrow LLM-as-judge for benchmark calibration. Your only task "
        "is to decide whether an already-generated evaluation matches the provided "
        "gold expectations. Focus on numeric agreement with the overall gold band "
        "and criterion-specific gold bands, plus whether the generated text captures "
        "expected strengths, expected weaknesses, expected key suggestions, and "
        "avoids forbidden claims. Do not judge general writing style. Do not reward "
        "a response merely because it sounds fluent. Return JSON only. Do not add "
        "markdown."
    )

    user_prompt = f"""Judge the following generated evaluation output.

Transcript ID: {transcript_id}
Transcript language: {transcript_language}
Variant name: {variant_name}
Expected benchmark quality band: {quality_band_block}

Retrieval configuration:
{retrieval_block}

Original transcript:
\"\"\"
{transcript}
\"\"\"

Retrieved evidence used by the variant:
{evidence_block}

Generated structured evaluation output:
{evaluation_block}

Benchmark notes:
{benchmark_notes_block}

Gold benchmark expectation:
{gold_block}

Judging rules:
- Judge the generated overall_score against gold_expected.overall_score_band.
- Judge each generated criterion score against gold_expected.criteria_expected.
- A score inside its band is calibrated; do not penalize it for not being at the
  midpoint.
- A score outside its band is miscalibrated. Penalize larger deviations more.
- Check whether the generated summary/suggestions reflect expected_strengths,
  expected_weaknesses, and expected_key_suggestion.
- Penalize any forbidden_claims that appear in the generated evaluation, even if
  numeric scores are inside band.
- Directional correctness means the generated evaluation places the case in the
  right quality direction: weak cases should not look strong, strong cases should
  not look weak, and mediocre/edge cases should remain moderate or mixed.

Rubric dimensions to score:
- overall_band_fit: Does the generated overall_score fall within the gold overall band?
- criterion_band_fit: Do the six generated criterion scores fall within their
  criterion-specific gold bands?
- benchmark_expectation_match: Does the text capture expected strengths,
  weaknesses, key suggestions, and avoid forbidden claims?
- directional_correctness: Is the generated evaluation directionally aligned
  with the expected quality band ({quality_band_block}) and benchmark notes?

Return exactly this JSON schema:
{judge_json_schema()}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
