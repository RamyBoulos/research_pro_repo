"""
Prompt builders for LLM-as-judge experiments over RAG technique outputs.

The judge receives:
  - the original transcript
  - retrieval metadata / evidence used by the variant
  - the structured evaluation output produced by the generator model

It returns a strict JSON rubric so we can compare variants consistently.
"""

from __future__ import annotations

import json


JUDGE_RUBRIC = [
    "transcript_faithfulness",
    "evidence_grounding",
    "specificity",
    "actionability",
    "criterion_alignment",
    "calibration",
    "overall_usefulness",
    "hallucination_risk",
]


def judge_json_schema() -> str:
    return """{
  "scores": {
    "transcript_faithfulness": "<integer 0-100, higher is better>",
    "evidence_grounding": "<integer 0-100, higher is better>",
    "specificity": "<integer 0-100, higher is better>",
    "actionability": "<integer 0-100, higher is better>",
    "criterion_alignment": "<integer 0-100, higher is better>",
    "calibration": "<integer 0-100, higher is better>",
    "overall_usefulness": "<integer 0-100, higher is better>",
    "hallucination_risk": "<integer 0-100, lower is better>"
  },
  "strengths": [
    "<short bullet point>"
  ],
  "weaknesses": [
    "<short bullet point>"
  ],
  "verdict": "<2-4 sentence professional judgment of this variant output>"
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
    Build a strict judge prompt for a single variant output.
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
        "You are a strict but fair evaluator of AI-generated educational feedback analyses. "
        "Your task is to judge the quality of a generated evaluation output, not to rewrite it. "
        "Use the transcript as primary evidence and the retrieved evidence as secondary context. "
        "When gold benchmark expectations are provided, use them as an additional calibration anchor. "
        "Do not reward an output for being more positive or more negative than the gold target; "
        "reward it for matching the intended benchmark calibration. "
        "Return JSON only. Do not add markdown. "
        "Score each rubric dimension as an integer 0-100. "
        "For hallucination_risk, lower is better. "
        "Keep strengths and weaknesses concise and concrete."
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

Rubric dimensions to score:
- transcript_faithfulness: Does the output accurately reflect what the transcript says?
- evidence_grounding: Does the output use retrieved evidence appropriately without over-claiming?
- specificity: Are strengths, weaknesses, and conclusions concrete rather than vague?
- actionability: Are the suggested improvements practical and usable?
- criterion_alignment: Does the output align with the intended six feedback-quality criteria?
- calibration: Are the scores and judgments appropriately strict and proportionate, especially relative to the gold benchmark expectation when provided?
- overall_usefulness: Would this output help train an examiner effectively?
- hallucination_risk: Does the output introduce unsupported claims? Lower is better.

Return exactly this JSON schema:
{judge_json_schema()}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
