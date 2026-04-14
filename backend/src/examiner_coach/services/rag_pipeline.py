from __future__ import annotations

import logging
from dataclasses import dataclass

from examiner_coach.config import settings
from examiner_coach.db.vector_store import query_collection
from examiner_coach.services.document_manager import (
    embed_query,
    format_passage_for_embedding,
    get_kisski_client,
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


def format_context_for_prompt(results: list[dict]) -> str:
    """
    Format retrieved chunks into a readable evidence block for prompt use.
    """
    sections = []
    for index, result in enumerate(results, start=1):
        methods = ", ".join(result.get("retrieval_methods", ["direct"]))
        sections.append(
            (
                f"[Source {index}: {result['source']} | "
                f"relevance={result['relevance']} | methods={methods}]\n"
                f"{result['text']}"
            )
        )
    return "\n\n".join(sections)


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
        "context_text": format_context_for_prompt(final_results),
        "used_hyde": config.use_hyde,
        "candidate_pool_size": config.candidate_pool_size,
        "final_k": config.final_k,
    }
