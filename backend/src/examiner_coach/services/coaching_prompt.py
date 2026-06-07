from __future__ import annotations

import json

from examiner_coach.api.schemas import (
    CoachingMessage,
    CoachingSessionSummary,
    Language,
    ResolvedEvaluationResult,
)


def coaching_json_schema() -> str:
    return """{
  "answer": {
    "en": "<natural coaching answer in English>",
    "de": "<natural coaching answer in German>"
  },
  "citation_requests": [
    {
      "evidence_id": "<integer evidence number from the retrieved evidence list>",
      "rationale": {
        "en": "<short explanation of why this source is relevant>",
        "de": "<kurze Begründung, warum diese Quelle relevant ist>"
      }
    }
  ],
  "updated_session_summary": {
    "language": "<'en' or 'de'>",
    "learner_needs": [
      "<short phrase>"
    ],
    "main_weaknesses": [
      "<short phrase>"
    ],
    "explained_criteria": [
      "<criterion id or short label already discussed>"
    ],
    "rewrite_examples_given": [
      "<short phrase>"
    ],
    "current_focus": "<short phrase or null>",
    "open_questions": [
      "<short phrase>"
    ]
  }
}"""


def _format_evaluation_block(evaluation: ResolvedEvaluationResult) -> str:
    criteria = [
        {
            "criterion_id": criterion.criterion_id,
            "label": criterion.label,
            "score_percent": criterion.score_percent,
            "suggestion": criterion.suggestion,
            "quote": criterion.quote,
        }
        for criterion in evaluation.criteria
    ]
    payload = {
        "overall_score": evaluation.overall_score,
        "summary": evaluation.summary,
        "criteria_met": evaluation.criteria_met,
        "total_criteria": evaluation.total_criteria,
        "criteria": criteria,
        "key_suggestion": evaluation.key_suggestion,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _format_conversation_history(conversation: list[CoachingMessage]) -> str:
    if not conversation:
        return "No previous turns."
    lines: list[str] = []
    for message in conversation[-8:]:
        role = "User" if message.role == "user" else "Assistant"
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


def _format_session_summary(summary: CoachingSessionSummary | None) -> str:
    if summary is None:
        return "No session summary yet."

    payload = {
        "language": summary.language.value,
        "learner_needs": summary.learner_needs,
        "main_weaknesses": summary.main_weaknesses,
        "explained_criteria": summary.explained_criteria,
        "rewrite_examples_given": summary.rewrite_examples_given,
        "current_focus": summary.current_focus,
        "open_questions": summary.open_questions,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_coaching_messages(
    *,
    transcript: str,
    evaluation: ResolvedEvaluationResult,
    user_message: str,
    conversation: list[CoachingMessage],
    session_summary: CoachingSessionSummary | None,
    output_language: Language,
    evidence_items: list[dict],
) -> list[dict[str, str]]:
    evidence_block = (
        json.dumps(evidence_items, ensure_ascii=False, indent=2)
        if evidence_items
        else "[]"
    )
    evaluation_block = _format_evaluation_block(evaluation)
    conversation_block = _format_conversation_history(conversation)
    summary_block = _format_session_summary(session_summary)

    system_prompt = (
        "You are a supportive examiner-feedback coach. "
        "Help the examiner understand the evaluation and improve their spoken "
        "feedback. "
        "Ground your answer first in the original transcript, second in the "
        "provided evaluation result, "
        "and third in the retrieved educational evidence. "
        "Be practical, concrete, and concise. "
        "When asked to improve wording, provide better example phrasing. "
        "Do not invent transcript details or citations. "
        "Return JSON only with both English and German answer fields, because "
        "the application resolves the display language afterwards. "
        "Only request citations when the retrieved evidence directly supports "
        "the answer. "
        "Do not request citations for thanks, greetings, acknowledgements, "
        "off-topic questions, or simple rewrite requests. "
        "Do not cite merely because evidence is available. "
        "Use at most 3 citations. "
        "Keep the rolling session summary compact and useful for future turns."
    )

    user_prompt = f"""Coach the examiner based on the following context.

Desired display language for this turn: {output_language.value}

Original transcript:
\"\"\"
{transcript}
\"\"\"

Resolved evaluation result:
{evaluation_block}

Rolling session summary:
{summary_block}

Recent conversation history:
{conversation_block}

Retrieved educational evidence:
{evidence_block}

Current user message:
\"\"\"
{user_message}
\"\"\"

Instructions:
- Answer the current question directly.
- Stay aligned with the provided evaluation unless the transcript clearly requires
  a careful clarification.
- If helpful, explain why the feedback was scored that way and how to improve it.
- If asked for a rewrite or example, provide natural-sounding better feedback wording.
- Leave citation_requests empty for thanks, greetings, acknowledgements,
  off-topic questions, or simple rewrite requests.
- Include citation_requests only when the current answer needs source-backed
  educational literature or scoring rationale, using only evidence ids from the
  evidence list.
- Update the session summary so later turns can stay consistent.

Return exactly this JSON schema:
{coaching_json_schema()}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
