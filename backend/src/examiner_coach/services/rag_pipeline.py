from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from examiner_coach.api.schemas import CriterionResult, EvaluationResult, Language
from examiner_coach.config import settings
from examiner_coach.db.vector_store import query_collection
from examiner_coach.services.document_manager import (
    embed_query,
    format_passage_for_embedding,
    get_kisski_client,
)
from examiner_coach.services.evaluation_prompt import (
    FEEDBACK_QUALITY_CRITERIA,
    build_prompt,
    compute_criteria_met,
    compute_overall_score,
    format_retrieved_context,
)

logger = logging.getLogger(__name__)

CRITERION_AWARE_RETRIEVAL_HINT = (
    "Find educational guidance about evaluating the quality of OSCE examiner feedback. "
    "Prioritize evidence about specific observed behavior, timely and contextual feedback, "
    "objective and non-evaluative tone, explicit strengths, changeable improvement areas, "
    "and concrete improvement plans or suggestions for change."
)

GUIDANCE_BONUS_PATTERNS = (
    "specific",
    "specific examples",
    "direct observation",
    "timely",
    "contextual",
    "neutral wording",
    "objective",
    "changeable",
    "behaviours that can be changed",
    "suggestions for change",
    "next steps",
    "action plan",
    "konkret",
    "beobacht",
    "zeitnah",
    "kontext",
    "objektiv",
    "veraenderbar",
    "veränderbar",
    "vorschlag",
    "naechste schritte",
    "nächste schritte",
)

LOW_VALUE_TEXT_PATTERNS = (
    "## references",
    "## literatur",
    "doi:",
    "urn:",
    "bibliography",
    "video-feedback",
)

GENERIC_OVERVIEW_SECTION_PATTERNS = (
    "feedback: why it is important",
    "why it is important",
    "conclusions",
    "abstract",
    "discussion",
    "introduction",
    "getting beyond 'good job'",
    "make feedback part of institutional culture",
    "practice points",
    "modelle zur wirkung von feedback",
)


@dataclass(slots=True)
class RetrievalInput:
    """
    Input payload for retrieval.
    The transcript remains the primary evidence source; HyDE is optional and
    only affects retrieval, not what is ultimately judged.
    """

    transcript: str
    user_query: str | None = None


@dataclass(slots=True)
class RetrievalConfig:
    """
    Retrieval configuration.
    `candidate_pool_size` controls how many chunks are pulled before final
    selection. When HyDE is enabled, half of this pool comes from direct
    retrieval and half from the hypothetical query.
    """

    retrieval_mode: Literal["none", "direct", "hyde"] = "direct"
    candidate_pool_size: int = 20
    final_k: int = 8
    use_hyde: bool = False
    hyde_max_tokens: int = 300
    normalize_to_english: bool = True
    criterion_aware_query: bool = True
    enable_quality_reranking: bool = True


def resolve_retrieval_mode(config: RetrievalConfig) -> Literal["none", "direct", "hyde"]:
    """
    Resolve the effective retrieval mode while keeping `use_hyde` backward
    compatible for older callers.
    """
    if config.use_hyde and config.retrieval_mode == "direct":
        return "hyde"
    return config.retrieval_mode


def build_retrieval_query(retrieval_input: RetrievalInput) -> str:
    """
    Build the direct retrieval query.
    Keep the transcript as the main evidence, optionally prefixed by a more
    focused user query if one is available.
    """
    transcript = retrieval_input.transcript.strip()
    user_query = (retrieval_input.user_query or "").strip()

    if user_query:
        return f"{user_query}\n\nTranscript:\n{transcript}"
    return transcript


def build_criterion_aware_query(retrieval_input: RetrievalInput) -> str:
    """
    Add task-specific hints so retrieval targets feedback-quality guidance
    instead of only semantic overlap with transcript wording.
    """
    base_query = build_retrieval_query(retrieval_input)
    return f"{CRITERION_AWARE_RETRIEVAL_HINT}\n\nTranscript to ground the search:\n{base_query}"


def generate_hypothetical_document(query: str, max_tokens: int) -> str:
    """
    Generate a hypothetical ideal answer for HyDE-style retrieval.
    This text is used only to retrieve candidate evidence, not to evaluate the
    transcript itself.
    """
    client = get_kisski_client()
    response = client.chat.completions.create(
        model=settings.kisski_llm_model,
        temperature=0.2,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "system",
                "content": (
                    "You help retrieve educational evidence. "
                    "Write a concise passage that would likely appear in "
                    "relevant academic or teaching guidance documents for the "
                    "given query. Keep it factual, compact, and under 180 words. "
                    "Do not mention that this is hypothetical."
                ),
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _is_likely_english(text: str) -> bool:
    """
    Lightweight heuristic for skipping translation when the transcript already
    looks English. This is intentionally conservative and optimized for the
    German-vs-English study setting.
    """
    lowered = text.lower()
    german_markers = ("ä", "ö", "ü", "ß", " beim ", " insgesamt ", " allerdings ")
    if any(marker in lowered for marker in german_markers):
        return False

    english_markers = (" the ", " and ", " overall ", " next time ", " however ")
    return any(marker in f" {lowered} " for marker in english_markers)


def translate_transcript_to_english(transcript: str) -> str:
    """
    Normalize any transcript into English before retrieval and evaluation.
    """
    if _is_likely_english(transcript):
        logger.info("Transcript appears to be English; skipping normalization step")
        return transcript

    try:
        client = get_kisski_client()
        response = client.chat.completions.create(
            model=settings.kisski_llm_model,
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise translator for clinical education text. "
                        "Translate the user's transcript into natural English while "
                        "preserving meaning, tone, omissions, and ambiguity. "
                        "Return only the translated transcript with no commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": transcript,
                },
            ],
        )
        normalized = (response.choices[0].message.content or "").strip()
        if not normalized:
            logger.warning("Transcript translation returned empty content; using original transcript")
            return transcript
        return normalized
    except Exception as exc:
        logger.warning("Transcript translation failed; using original transcript. Error: %s", exc)
        return transcript


def retrieve_direct(query: str, k: int) -> list[dict]:
    """
    Retrieve candidate chunks directly from the user/transcript query.
    """
    query_embedding = embed_query(query)
    results = query_collection(query_embedding, n_results=k)
    for result in results:
        result["retrieval_method"] = "direct"
    return results


def retrieve_hyde(query: str, k: int, max_tokens: int) -> list[dict]:
    """
    Retrieve candidate chunks using a HyDE-generated hypothetical passage.
    """
    hypothetical_document = generate_hypothetical_document(query, max_tokens=max_tokens)
    if not hypothetical_document:
        logger.warning("HyDE generation returned empty content; skipping HyDE retrieval")
        return []

    # HyDE generates a document-like passage, so embed it in the same
    # passage-style space as stored chunks.
    passage_text = format_passage_for_embedding(hypothetical_document)
    client = get_kisski_client()
    response = client.embeddings.create(
        input=[passage_text],
        model=settings.kisski_embedding_model,
    )
    query_embedding = response.data[0].embedding
    results = query_collection(query_embedding, n_results=k)
    for result in results:
        result["retrieval_method"] = "hyde"
        result["hyde_query"] = hypothetical_document
    return results


def deduplicate_candidates(candidates: list[dict]) -> list[dict]:
    """
    Deduplicate retrieval results by source + text and merge repeated hits.
    If a chunk appears through multiple retrieval paths, keep the highest
    relevance and record all retrieval methods that found it.
    """
    deduplicated: dict[tuple[str, str], dict] = {}

    for candidate in candidates:
        key = (candidate["source"], candidate["text"])
        if key not in deduplicated:
            deduplicated[key] = {
                "text": candidate["text"],
                "source": candidate["source"],
                "relevance": candidate["relevance"],
                "retrieval_methods": [candidate["retrieval_method"]],
                "metadata": candidate.get("metadata") or {},
            }
            continue

        current = deduplicated[key]
        current["relevance"] = max(current["relevance"], candidate["relevance"])
        if candidate["retrieval_method"] not in current["retrieval_methods"]:
            current["retrieval_methods"].append(candidate["retrieval_method"])
        if not current.get("metadata") and candidate.get("metadata"):
            current["metadata"] = candidate["metadata"]

    return sorted(deduplicated.values(), key=lambda item: item["relevance"], reverse=True)


def _normalize_text_for_matching(text: str) -> str:
    return (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


def _count_guidance_hits(text: str) -> int:
    normalized = _normalize_text_for_matching(text)
    return sum(1 for pattern in GUIDANCE_BONUS_PATTERNS if pattern in normalized)


def _looks_like_low_value_chunk(candidate: dict) -> bool:
    metadata = candidate.get("metadata") or {}
    if metadata.get("is_low_value") is True:
        return True

    chunk_type = str(metadata.get("chunk_type", "")).lower()
    if chunk_type == "references":
        return True

    normalized = _normalize_text_for_matching(candidate.get("text", ""))
    if any(pattern in normalized for pattern in LOW_VALUE_TEXT_PATTERNS):
        return True

    non_empty_lines = [line.strip() for line in candidate.get("text", "").splitlines() if line.strip()]
    if not non_empty_lines:
        return True

    short_lines = sum(1 for line in non_empty_lines if len(line) < 120)
    doi_count = normalized.count("doi:")
    bullet_count = len(re.findall(r"(?m)^\s*-\s", candidate.get("text", "")))
    return doi_count >= 2 or (short_lines / len(non_empty_lines) > 0.8 and bullet_count >= 3)


def _score_candidate_quality(candidate: dict) -> tuple[float, list[str]]:
    metadata = candidate.get("metadata") or {}
    text = candidate.get("text", "")
    normalized = _normalize_text_for_matching(text)
    score = float(candidate.get("relevance", 0.0))
    reasons: list[str] = []

    section_label = str(metadata.get("section_label") or "")
    if section_label:
        guidance_hits = _count_guidance_hits(section_label)
        if guidance_hits:
            score += min(0.03 * guidance_hits, 0.12)
            reasons.append("guidance-section")

    content_hits = _count_guidance_hits(text)
    if content_hits:
        score += min(0.025 * content_hits, 0.15)
        reasons.append("guidance-keywords")

    chunk_type = str(metadata.get("chunk_type", "")).lower()
    if chunk_type == "guidance":
        score += 0.08
        reasons.append("guidance-type")
    elif chunk_type == "conclusion":
        score -= 0.05
        reasons.append("generic-conclusion")
    elif chunk_type == "abstract":
        score -= 0.03
        reasons.append("abstract")

    if "direct observation" in normalized or "beobacht" in normalized:
        score += 0.05
        reasons.append("direct-observation")
    if (
        "suggestions for change" in normalized
        or "next steps" in normalized
        or "naechste schritte" in normalized
    ):
        score += 0.05
        reasons.append("actionable-guidance")

    section_label_normalized = _normalize_text_for_matching(section_label)
    if any(pattern in section_label_normalized for pattern in GENERIC_OVERVIEW_SECTION_PATTERNS):
        score -= 0.08
        reasons.append("generic-section")

    if (
        "why it is important" in normalized
        or normalized.startswith("## conclusions")
        or normalized.startswith("## abstract")
        or "institutional culture" in normalized
    ):
        score -= 0.06
        reasons.append("generic-content")

    if _looks_like_low_value_chunk(candidate):
        score -= 0.25
        reasons.append("low-value")

    return round(score, 4), reasons


def retrieve_candidates(
    retrieval_input: RetrievalInput,
    config: RetrievalConfig | None = None,
) -> list[dict]:
    """
    Retrieve candidate chunks using direct retrieval and optional HyDE.
    When HyDE is enabled, half the candidate pool is retrieved directly and
    the other half via the hypothetical document query.
    """
    config = config or RetrievalConfig()
    retrieval_mode = resolve_retrieval_mode(config)
    base_query = (
        build_criterion_aware_query(retrieval_input)
        if config.criterion_aware_query
        else build_retrieval_query(retrieval_input)
    )

    if retrieval_mode == "none":
        return []

    if retrieval_mode == "direct":
        return retrieve_direct(base_query, config.candidate_pool_size)

    direct_k = max(1, config.candidate_pool_size // 2)
    hyde_k = max(1, config.candidate_pool_size - direct_k)

    direct_candidates = retrieve_direct(base_query, direct_k)
    hyde_candidates = retrieve_hyde(
        base_query,
        hyde_k,
        max_tokens=config.hyde_max_tokens,
    )
    return deduplicate_candidates(direct_candidates + hyde_candidates)


def select_final_context(
    candidates: list[dict],
    config: RetrievalConfig,
) -> list[dict]:
    """
    Select the final retrieval results after optional quality reranking.
    """
    if not config.enable_quality_reranking:
        return sorted(candidates, key=lambda item: item["relevance"], reverse=True)[: config.final_k]

    rescored_candidates: list[dict] = []
    for candidate in candidates:
        reranked_score, rerank_reasons = _score_candidate_quality(candidate)
        updated = dict(candidate)
        updated["raw_relevance"] = candidate.get("relevance", 0.0)
        updated["relevance"] = reranked_score
        updated["rerank_reasons"] = rerank_reasons
        rescored_candidates.append(updated)

    filtered = [candidate for candidate in rescored_candidates if not _looks_like_low_value_chunk(candidate)]
    final_pool = filtered or rescored_candidates
    return sorted(final_pool, key=lambda item: item["relevance"], reverse=True)[: config.final_k]


def build_rag_context(
    retrieval_input: RetrievalInput,
    config: RetrievalConfig | None = None,
) -> dict:
    """
    Build a full RAG context package for downstream evaluation.
    """
    config = config or RetrievalConfig()
    retrieval_mode = resolve_retrieval_mode(config)

    if retrieval_mode == "none":
        return {
            "query": (
                build_criterion_aware_query(retrieval_input)
                if config.criterion_aware_query
                else build_retrieval_query(retrieval_input)
            ),
            "results": [],
            "context_text": "No relevant evidence retrieved from the knowledge base.",
            "used_hyde": False,
            "retrieval_mode": "none",
            "candidate_pool_size": 0,
            "final_k": 0,
        }

    candidates = retrieve_candidates(retrieval_input, config=config)
    final_results = select_final_context(candidates, config=config)
    query = (
        build_criterion_aware_query(retrieval_input)
        if config.criterion_aware_query
        else build_retrieval_query(retrieval_input)
    )

    return {
        "query": query,
        "results": final_results,
        "context_text": format_retrieved_context(final_results),
        "used_hyde": retrieval_mode == "hyde",
        "retrieval_mode": retrieval_mode,
        "candidate_pool_size": config.candidate_pool_size,
        "final_k": config.final_k,
    }


def _clean_llm_output(raw: str) -> str:
    """
    Strip common markdown fence artifacts before JSON parsing.
    """
    cleaned = raw.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return "\n".join(lines[1:]).strip()


def _build_missing_suggestion(criterion_id: str) -> dict[Language, str]:
    """
    Fallback short suggestion used when the LLM omits the criterion suggestion.
    """
    return {
        Language.EN: f"Add a clearer improvement point for '{criterion_id}'.",
        Language.DE: f"Ergaenzen Sie einen klareren Verbesserungshinweis fuer '{criterion_id}'.",
    }


def _build_missing_summary() -> dict[Language, str]:
    """
    Fallback overall summary used when the LLM omits the summary field.
    """
    return {
        Language.EN: "No overall summary was returned.",
        Language.DE: "Es wurde keine Gesamtzusammenfassung zurueckgegeben.",
    }


def _parse_llm_response(
    raw: str,
    transcript: str,
    duration_seconds: float,
) -> EvaluationResult:
    """
    Parse raw LLM output into a validated EvaluationResult.
    """
    cleaned = _clean_llm_output(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "LLM returned unparseable JSON. "
            f"Raw output (first 500 chars): {raw[:500]!r}. Error: {exc}"
        ) from exc

    raw_items = data.get("criteria", [])
    if not isinstance(raw_items, list):
        logger.warning("LLM returned non-list 'criteria'; treating as empty")
        raw_items = []

    raw_criteria: dict[str, dict] = {}
    unknown_ids: list[str] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        criterion_id = item.get("criterion_id")
        if not criterion_id:
            continue
        if any(definition["id"] == criterion_id for definition in FEEDBACK_QUALITY_CRITERIA):
            raw_criteria[criterion_id] = item
        else:
            unknown_ids.append(str(criterion_id))

    if unknown_ids:
        logger.warning("LLM returned unknown criterion ids: %s", ", ".join(unknown_ids))

    criteria_results: list[CriterionResult] = []
    missing_ids: list[str] = []

    for definition in FEEDBACK_QUALITY_CRITERIA:
        criterion_id = definition["id"]
        raw_item = raw_criteria.get(criterion_id)
        if raw_item is None:
            missing_ids.append(criterion_id)
            raw_item = {}

        score_raw = raw_item.get("score_percent", 0)
        try:
            score_value = float(score_raw)
        except (TypeError, ValueError):
            score_value = 0.0
        score = round(max(0.0, min(100.0, score_value)))

        suggestion_raw = raw_item.get("suggestion")
        if isinstance(suggestion_raw, dict):
            suggestion = {
                Language.EN: str(
                    suggestion_raw.get("en")
                    or _build_missing_suggestion(criterion_id)[Language.EN]
                ),
                Language.DE: str(
                    suggestion_raw.get("de")
                    or _build_missing_suggestion(criterion_id)[Language.DE]
                ),
            }
        else:
            suggestion = _build_missing_suggestion(criterion_id)

        quote_raw = raw_item.get("quote")
        if isinstance(quote_raw, dict) and quote_raw.get("en") and quote_raw.get("de"):
            quote = {
                Language.EN: str(quote_raw["en"]),
                Language.DE: str(quote_raw["de"]),
            }
        else:
            quote = None

        criteria_results.append(
            CriterionResult(
                criterion_id=criterion_id,
                label={
                    Language.EN: definition["label"]["en"],
                    Language.DE: definition["label"]["de"],
                },
                score_percent=score,
                suggestion=suggestion,
                quote=quote,
            )
        )

    if missing_ids:
        logger.warning("LLM omitted criteria: %s", ", ".join(missing_ids))

    scores = [criterion.score_percent for criterion in criteria_results]
    overall_score = compute_overall_score(scores)
    criteria_met = compute_criteria_met(scores)

    summary_raw = data.get("summary")
    if isinstance(summary_raw, dict):
        summary = {
            Language.EN: str(summary_raw.get("en") or _build_missing_summary()[Language.EN]),
            Language.DE: str(summary_raw.get("de") or _build_missing_summary()[Language.DE]),
        }
    else:
        summary = _build_missing_summary()

    key_suggestion_raw = data.get("key_suggestion")
    if isinstance(key_suggestion_raw, dict):
        key_suggestion = {
            Language.EN: str(key_suggestion_raw.get("en") or "No suggestion provided."),
            Language.DE: str(key_suggestion_raw.get("de") or "Kein Vorschlag angegeben."),
        }
    else:
        key_suggestion = {
            Language.EN: "No suggestion provided.",
            Language.DE: "Kein Vorschlag angegeben.",
        }

    return EvaluationResult(
        transcript=transcript,
        duration_seconds=duration_seconds,
        overall_score=overall_score,
        summary=summary,
        criteria_met=criteria_met,
        total_criteria=len(FEEDBACK_QUALITY_CRITERIA),
        criteria=criteria_results,
        key_suggestion=key_suggestion,
    )


def evaluate_transcript_with_details(
    transcript: str,
    duration_seconds: float,
    config: RetrievalConfig | None = None,
) -> dict:
    """
    Full evaluation pipeline with detailed intermediate artifacts for
    experiments and judging.
    """
    transcript = transcript.strip()
    if not transcript:
        raise ValueError("Transcript must not be empty.")

    config = config or RetrievalConfig()
    normalized_transcript = (
        translate_transcript_to_english(transcript)
        if config.normalize_to_english
        else transcript
    )

    logger.info(
        "Starting transcript evaluation (mode=%s, normalize=%s)",
        resolve_retrieval_mode(config),
        config.normalize_to_english,
    )
    rag_context = build_rag_context(
        RetrievalInput(transcript=normalized_transcript),
        config=config,
    )
    logger.info(
        "Retrieved %d final chunks from pool=%d",
        len(rag_context["results"]),
        rag_context["candidate_pool_size"],
    )

    messages = build_prompt(
        transcript=normalized_transcript,
        context_text=rag_context["context_text"],
        duration_seconds=duration_seconds,
    )

    logger.info("Calling Kisski LLM model: %s", settings.kisski_llm_model)
    client = get_kisski_client()
    response = client.chat.completions.create(
        model=settings.kisski_llm_model,
        messages=messages,
        temperature=0.0,
        max_tokens=2000,
    )

    raw_output = (response.choices[0].message.content or "").strip()
    logger.debug("LLM raw output preview: %s", raw_output[:300])

    result = _parse_llm_response(
        raw=raw_output,
        transcript=transcript,
        duration_seconds=duration_seconds,
    )

    logger.info(
        "Evaluation complete: overall_score=%d, criteria_met=%d/%d",
        result.overall_score,
        result.criteria_met,
        result.total_criteria,
    )
    return {
        "result": result,
        "normalized_transcript": normalized_transcript,
        "rag_context": rag_context,
        "raw_output": raw_output,
        "messages": messages,
        "retrieval_config": {
            "retrieval_mode": resolve_retrieval_mode(config),
            "candidate_pool_size": config.candidate_pool_size,
            "final_k": config.final_k,
            "hyde_max_tokens": config.hyde_max_tokens,
            "normalize_to_english": config.normalize_to_english,
            "criterion_aware_query": config.criterion_aware_query,
            "enable_quality_reranking": config.enable_quality_reranking,
        },
    }


def evaluate_transcript(
    transcript: str,
    duration_seconds: float,
    config: RetrievalConfig | None = None,
) -> EvaluationResult:
    """
    Production-facing wrapper that returns only the parsed evaluation result.
    """
    details = evaluate_transcript_with_details(
        transcript=transcript,
        duration_seconds=duration_seconds,
        config=config,
    )
    return details["result"]
