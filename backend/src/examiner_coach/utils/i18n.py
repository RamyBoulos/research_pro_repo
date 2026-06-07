from examiner_coach.api.schemas import (
    CoachingCitation,
    CoachingResponse,
    CriterionResult,
    EvaluationResult,
    Language,
    ResolvedCoachingCitation,
    ResolvedCoachingResponse,
    ResolvedCriterionResult,
    ResolvedEvaluationResult,
)


def get_text(content: dict[Language, str], lang: Language) -> str:
    """
    Safely resolve bilingual text with English fallback.
    """
    if lang in content:
        return content[lang]
    return content[Language.EN]


def resolve_criterion_result(
    criterion: CriterionResult,
    lang: Language,
) -> ResolvedCriterionResult:
    """
    Convert one bilingual criterion result into a single-language display view.
    """
    return ResolvedCriterionResult(
        criterion_id=criterion.criterion_id,
        label=get_text(criterion.label, lang),
        score_percent=criterion.score_percent,
        suggestion=get_text(criterion.suggestion, lang),
        quote=get_text(criterion.quote, lang) if criterion.quote else None,
    )


def resolve_evaluation_result(
    evaluation: EvaluationResult,
    lang: Language = Language.EN,
) -> ResolvedEvaluationResult:
    """
    Convert the canonical bilingual evaluation into a single-language view.
    This supports presentation-time language switching without regenerating the
    underlying evaluation.
    """
    return ResolvedEvaluationResult(
        output_language=lang,
        transcript=evaluation.transcript,
        duration_seconds=evaluation.duration_seconds,
        overall_score=evaluation.overall_score,
        summary=get_text(evaluation.summary, lang),
        criteria_met=evaluation.criteria_met,
        total_criteria=evaluation.total_criteria,
        criteria=[
            resolve_criterion_result(criterion, lang)
            for criterion in evaluation.criteria
        ],
        key_suggestion=get_text(evaluation.key_suggestion, lang),
    )


def resolve_coaching_citation(
    citation: CoachingCitation,
    lang: Language,
) -> ResolvedCoachingCitation:
    return ResolvedCoachingCitation(
        source=citation.source,
        section=citation.section,
        quote=get_text(citation.quote, lang) if citation.quote else None,
        rationale=get_text(citation.rationale, lang) if citation.rationale else None,
    )


def resolve_coaching_response(
    coaching: CoachingResponse,
    lang: Language = Language.DE,
) -> ResolvedCoachingResponse:
    return ResolvedCoachingResponse(
        output_language=lang,
        answer=get_text(coaching.answer, lang),
        citations=[
            resolve_coaching_citation(citation, lang)
            for citation in coaching.citations
        ],
        updated_session_summary=coaching.updated_session_summary,
    )
