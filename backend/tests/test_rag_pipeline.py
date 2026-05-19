from examiner_coach.services.rag_pipeline import (
    RetrievalConfig,
    RetrievalInput,
    build_rag_context,
    resolve_retrieval_mode,
)


def test_resolve_retrieval_mode_keeps_direct_default() -> None:
    config = RetrievalConfig()
    assert resolve_retrieval_mode(config) == "direct"


def test_resolve_retrieval_mode_supports_use_hyde_backcompat() -> None:
    config = RetrievalConfig(use_hyde=True)
    assert resolve_retrieval_mode(config) == "hyde"


def test_build_rag_context_none_mode_skips_retrieval() -> None:
    config = RetrievalConfig(retrieval_mode="none", candidate_pool_size=0, final_k=0)
    context = build_rag_context(
        retrieval_input=RetrievalInput(
            transcript="The student asked clear follow-up questions."
        ),
        config=config,
    )
    assert context["retrieval_mode"] == "none"
    assert context["results"] == []
    assert context["final_k"] == 0
    assert "No relevant evidence retrieved" in context["context_text"]
