import logging

from fastapi import APIRouter, HTTPException

from examiner_coach.api.schemas import (
    EvaluationRequest,
    EvaluationResult,
    ResolvedEvaluationResult,
)
from examiner_coach.services.rag_pipeline import evaluate_transcript
from examiner_coach.utils.i18n import resolve_evaluation_result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/evaluate", response_model=ResolvedEvaluationResult)
async def evaluate_feedback(request: EvaluationRequest) -> ResolvedEvaluationResult:
    """
    Run the full RAG evaluation pipeline and return the resolved language view.
    """
    logger.info(
        "Evaluation request received: duration=%.1fs, lang=%s, transcript_len=%d",
        request.duration_seconds,
        request.output_language,
        len(request.transcript),
    )

    try:
        result: EvaluationResult = evaluate_transcript(
            transcript=request.transcript,
            duration_seconds=request.duration_seconds,
        )
    except ValueError as exc:
        logger.error("Evaluation pipeline rejected request: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during evaluation")
        raise HTTPException(
            status_code=500,
            detail="Evaluation failed due to an internal error.",
        ) from exc

    return resolve_evaluation_result(result, lang=request.output_language)


@router.post("/evaluate/full", response_model=EvaluationResult)
async def evaluate_feedback_full(request: EvaluationRequest) -> EvaluationResult:
    """
    Run the full RAG evaluation pipeline and return the canonical bilingual
    result so clients can switch display language without regenerating.
    """
    logger.info(
        "Full evaluation request received: duration=%.1fs, transcript_len=%d",
        request.duration_seconds,
        len(request.transcript),
    )

    try:
        return evaluate_transcript(
            transcript=request.transcript,
            duration_seconds=request.duration_seconds,
        )
    except ValueError as exc:
        logger.error("Evaluation pipeline rejected request: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during full evaluation")
        raise HTTPException(
            status_code=500,
            detail="Evaluation failed due to an internal error.",
        ) from exc
