from __future__ import annotations

import json
import logging
import re
from typing import Literal

from fastapi import APIRouter, HTTPException

from examiner_coach.api.schemas import (
    CoachingCitation,
    CoachingRequest,
    CoachingResponse,
    CoachingSessionSummary,
    Language,
    ResolvedCoachingResponse,
)
from examiner_coach.config import settings
from examiner_coach.services.coaching_prompt import build_coaching_messages
from examiner_coach.services.document_manager import get_kisski_client
from examiner_coach.services.rag_pipeline import (
    RetrievalConfig,
    RetrievalInput,
    build_rag_context,
    translate_transcript_to_english,
)
from examiner_coach.utils.i18n import resolve_coaching_response

logger = logging.getLogger(__name__)

router = APIRouter()

CoachingIntent = Literal[
    "coaching_question",
    "evidence_question",
    "rewrite_request",
    "social",
    "off_topic",
]

SOCIAL_PATTERNS = (
    (
        r"^(thanks?|thank you|danke|vielen dank|merci|ok(?:ay)?|"
        r"alles klar|verstanden)[.! ]*$"
    ),
    r"^(hi|hello|hey|hallo|guten morgen|guten tag|guten abend)[.! ]*$",
)

OFF_TOPIC_PATTERNS = (
    r"\b(weather|temperature|forecast|rain|snow|sunny)\b",
    r"\b(wetter|temperatur|vorhersage|regen|schnee|sonnig)\b",
    r"\b(time|date|today|tomorrow|yesterday)\b",
    r"\b(uhrzeit|datum|heute|morgen|gestern)\b",
)

REWRITE_PATTERNS = (
    r"\b(rewrite|rephrase|word(?:ing)?|phrase|formulat(?:e|ion)|example)\b",
    r"\b(umformulieren|formulieren|formulierung|beispiel|besser sagen|anders sagen)\b",
)

EVIDENCE_PATTERNS = (
    r"\b(source|sources|citation|citations|evidence|literature|study|paper|reference|references)\b",
    r"\b(quelle|quellen|beleg|belege|evidenz|literatur|studie|paper|referenz|referenzen)\b",
)

RATIONALE_PATTERNS = (
    r"\b(why|how come|rationale|scor(?:e|ed|ing)|grade|graded|evaluation)\b",
    r"\b(warum|wieso|weshalb|begründung|bewertung|bewertet|punktzahl|score)\b",
)


def _clean_json(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return "\n".join(lines[1:]).strip()
    return cleaned


def _safe_excerpt(text: str, limit: int = 220) -> str:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def classify_coaching_intent(user_message: str) -> CoachingIntent:
    """
    Classify the current turn before retrieval.
    This keeps source display a product decision instead of leaving it entirely
    to the model whenever evidence happens to be available.
    """
    normalized = " ".join(user_message.strip().lower().split())
    if not normalized:
        return "social"

    if _matches_any(normalized, SOCIAL_PATTERNS):
        return "social"

    if _matches_any(normalized, OFF_TOPIC_PATTERNS):
        return "off_topic"

    if _matches_any(normalized, EVIDENCE_PATTERNS) or _matches_any(
        normalized, RATIONALE_PATTERNS
    ):
        return "evidence_question"

    if _matches_any(normalized, REWRITE_PATTERNS):
        return "rewrite_request"

    return "coaching_question"


def _should_retrieve_evidence(intent: CoachingIntent) -> bool:
    return intent in {"coaching_question", "evidence_question"}


def _should_allow_citations(intent: CoachingIntent) -> bool:
    return intent in {"coaching_question", "evidence_question"}


def apply_citation_policy(
    coaching: CoachingResponse,
    intent: CoachingIntent,
) -> CoachingResponse:
    if not _should_allow_citations(intent):
        coaching.citations = []
    return coaching


def _build_evidence_items(results: list[dict]) -> list[dict]:
    evidence_items: list[dict] = []
    for index, result in enumerate(results, start=1):
        metadata = result.get("metadata") or {}
        section = metadata.get("section_label")
        evidence_items.append(
            {
                "evidence_id": index,
                "source": result.get("source"),
                "section": section,
                "retrieval_methods": result.get("retrieval_methods")
                or [result.get("retrieval_method")],
                "excerpt": _safe_excerpt(result.get("text", "")),
            }
        )
    return evidence_items


def _parse_summary(data: dict, output_language: Language) -> CoachingSessionSummary:
    summary_raw = data.get("updated_session_summary")
    if not isinstance(summary_raw, dict):
        return CoachingSessionSummary(language=output_language)

    language_raw = summary_raw.get("language", output_language.value)
    try:
        language = Language(language_raw)
    except Exception:
        language = output_language

    def string_list(key: str) -> list[str]:
        values = summary_raw.get(key, [])
        if not isinstance(values, list):
            return []
        return [str(value).strip() for value in values if str(value).strip()]

    current_focus_raw = summary_raw.get("current_focus")
    current_focus = str(current_focus_raw).strip() if current_focus_raw else None

    return CoachingSessionSummary(
        language=language,
        learner_needs=string_list("learner_needs"),
        main_weaknesses=string_list("main_weaknesses"),
        explained_criteria=string_list("explained_criteria"),
        rewrite_examples_given=string_list("rewrite_examples_given"),
        current_focus=current_focus,
        open_questions=string_list("open_questions"),
    )


def _parse_coaching_response(
    raw: str,
    *,
    evidence_items: list[dict],
    output_language: Language,
) -> CoachingResponse:
    data = json.loads(_clean_json(raw))

    answer_raw = data.get("answer")
    if isinstance(answer_raw, dict):
        answer = {
            Language.EN: str(answer_raw.get("en") or "No answer provided."),
            Language.DE: str(answer_raw.get("de") or "Keine Antwort angegeben."),
        }
    else:
        text = str(answer_raw or "").strip()
        answer = {
            Language.EN: text or "No answer provided.",
            Language.DE: text or "Keine Antwort angegeben.",
        }

    evidence_map = {item["evidence_id"]: item for item in evidence_items}
    citations: list[CoachingCitation] = []
    citation_requests = data.get("citation_requests", [])
    if isinstance(citation_requests, list):
        for item in citation_requests[:3]:
            if not isinstance(item, dict):
                continue
            evidence_id = item.get("evidence_id")
            if not isinstance(evidence_id, int) or evidence_id not in evidence_map:
                continue

            evidence = evidence_map[evidence_id]
            rationale_raw = item.get("rationale")
            if isinstance(rationale_raw, dict):
                rationale = {
                    Language.EN: str(rationale_raw.get("en") or ""),
                    Language.DE: str(rationale_raw.get("de") or ""),
                }
            else:
                rationale = None

            quote_excerpt = evidence["excerpt"]
            citations.append(
                CoachingCitation(
                    source=str(evidence["source"]),
                    section=(
                        str(evidence["section"]) if evidence.get("section") else None
                    ),
                    quote={
                        Language.EN: quote_excerpt,
                        Language.DE: quote_excerpt,
                    },
                    rationale=rationale,
                )
            )

    return CoachingResponse(
        answer=answer,
        citations=citations,
        updated_session_summary=_parse_summary(data, output_language),
    )


@router.post("/coach", response_model=ResolvedCoachingResponse)
async def coach_examiner(request: CoachingRequest) -> ResolvedCoachingResponse:
    intent = classify_coaching_intent(request.user_message)
    logger.info(
        "Coaching request received: lang=%s, transcript_len=%d, turns=%d, intent=%s",
        request.output_language,
        len(request.transcript),
        len(request.conversation),
        intent,
    )

    config = RetrievalConfig(
        retrieval_mode="hyde",
        candidate_pool_size=20,
        final_k=8,
        hyde_max_tokens=300,
        normalize_to_english=True,
        criterion_aware_query=True,
        enable_quality_reranking=True,
    )

    evidence_items: list[dict] = []
    if _should_retrieve_evidence(intent):
        normalized_transcript = (
            translate_transcript_to_english(request.transcript)
            if config.normalize_to_english
            else request.transcript
        )
        rag_context = build_rag_context(
            RetrievalInput(
                transcript=normalized_transcript,
                user_query=request.user_message,
            ),
            config=config,
        )
        evidence_items = _build_evidence_items(rag_context["results"])

    messages = build_coaching_messages(
        transcript=request.transcript,
        evaluation=request.evaluation,
        user_message=request.user_message,
        conversation=request.conversation,
        session_summary=request.session_summary,
        output_language=request.output_language,
        evidence_items=evidence_items,
    )

    try:
        client = get_kisski_client()
        response = client.chat.completions.create(
            model=settings.kisski_llm_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1400,
        )
        raw_output = (response.choices[0].message.content or "").strip()
        coaching = _parse_coaching_response(
            raw_output,
            evidence_items=evidence_items,
            output_language=request.output_language,
        )
        coaching = apply_citation_policy(coaching, intent)
    except ValueError as exc:
        logger.error("Coaching response could not be parsed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during coaching")
        raise HTTPException(
            status_code=500,
            detail="Coaching failed due to an internal error.",
        ) from exc

    return resolve_coaching_response(coaching, lang=request.output_language)
