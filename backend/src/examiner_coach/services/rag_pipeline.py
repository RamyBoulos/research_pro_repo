from __future__ import annotations

import json
import logging
from dataclasses import dataclass

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

    candidate_pool_size: int = 20
    final_k: int = 8
    use_hyde: bool = False
    hyde_max_tokens: int = 300


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
            }
            continue

        current = deduplicated[key]
        current["relevance"] = max(current["relevance"], candidate["relevance"])
        if candidate["retrieval_method"] not in current["retrieval_methods"]:
            current["retrieval_methods"].append(candidate["retrieval_method"])

    return sorted(deduplicated.values(), key=lambda item: item["relevance"], reverse=True)


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
    base_query = build_retrieval_query(retrieval_input)

    if not config.use_hyde:
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
    final_k: int,
) -> list[dict]:
    """
    Select the final top-ranked retrieval results.
    """
    return sorted(candidates, key=lambda item: item["relevance"], reverse=True)[:final_k]


def build_rag_context(
    retrieval_input: RetrievalInput,
    config: RetrievalConfig | None = None,
) -> dict:
    """
    Build a full RAG context package for downstream evaluation.
    """
    config = config or RetrievalConfig()
    candidates = retrieve_candidates(retrieval_input, config=config)
    final_results = select_final_context(candidates, final_k=config.final_k)

    return {
        "query": build_retrieval_query(retrieval_input),
        "results": final_results,
        "context_text": format_retrieved_context(final_results),
        "used_hyde": config.use_hyde,
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


def evaluate_transcript(
    transcript: str,
    duration_seconds: float,
    config: RetrievalConfig | None = None,
) -> EvaluationResult:
    """
    Full RAG evaluation pipeline: retrieve, prompt, call LLM, parse, return.
    """
    transcript = transcript.strip()
    if not transcript:
        raise ValueError("Transcript must not be empty.")

    config = config or RetrievalConfig()
    normalized_transcript = translate_transcript_to_english(transcript)

    logger.info("Starting transcript evaluation (HyDE=%s)", config.use_hyde)
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
    return result
