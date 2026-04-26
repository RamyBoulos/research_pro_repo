from examiner_coach.api.schemas import (
    CriterionResult,
    EvaluationResult,
    Language,
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
        comment=get_text(criterion.comment, lang),
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
        criteria_met=evaluation.criteria_met,
        total_criteria=evaluation.total_criteria,
        criteria=[
            resolve_criterion_result(criterion, lang)
            for criterion in evaluation.criteria
        ],
        key_suggestion=get_text(evaluation.key_suggestion, lang),
    )
