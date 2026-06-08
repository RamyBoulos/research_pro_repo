from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


# Shared enums
class Language(StrEnum):
    EN = "en"
    DE = "de"


# Audio / transcription
class TranscriptionResponse(BaseModel):
    transcript: str
    duration_seconds: float


# Evaluation
class EvaluationRequest(BaseModel):
    """Input payload for evaluating an examiner feedback transcript."""

    transcript: str = Field(min_length=1, description="Transcript text to evaluate")
    duration_seconds: float = Field(ge=0.0, description="Audio duration in seconds")
    output_language: Language = Field(
        default=Language.EN,
        description="Preferred language for displaying the result",
    )


class CriterionResult(BaseModel):
    """Result for a single feedback quality criterion."""

    criterion_id: str = Field(description="Unique identifier e.g. 'specific_behavior'")
    label: dict[Language, str] = Field(description="Human-readable label in EN and DE")
    score_percent: int = Field(
        ge=0,
        le=100,
        description=(
            "How strongly the criterion was met, expressed as an integer "
            "percentage"
        ),
    )
    suggestion: dict[Language, str] = Field(
        description="Very short one-sentence improvement suggestion in EN and DE"
    )
    quote: dict[Language, str] | None = Field(
        default=None,
        description="Relevant quote from transcript, if applicable"
    )


class EvaluationResult(BaseModel):
    """Full feedback quality evaluation returned to the frontend."""

    transcript: str
    duration_seconds: float
    overall_score: int = Field(ge=0, le=100, description="Integer percentage 0-100")
    summary: dict[Language, str] = Field(
        description="Short overall summary of the feedback quality in EN and DE"
    )
    criteria_met: int
    total_criteria: int
    criteria: list[CriterionResult]
    key_suggestion: dict[Language, str] = Field(
        description="Single most important improvement tip in EN and DE"
    )


class ResolvedCriterionResult(BaseModel):
    """Single-language view of a feedback quality criterion for display or export."""

    criterion_id: str
    label: str
    score_percent: int = Field(
        ge=0,
        le=100,
        description=(
            "How strongly the criterion was met, expressed as an integer "
            "percentage"
        ),
    )
    suggestion: str
    quote: str | None = None


class ResolvedEvaluationResult(BaseModel):
    """Single-language view of an evaluation resolved from the bilingual result."""

    output_language: Language
    transcript: str
    duration_seconds: float
    overall_score: int = Field(ge=0, le=100, description="Integer percentage 0-100")
    summary: str
    criteria_met: int
    total_criteria: int
    criteria: list[ResolvedCriterionResult]
    key_suggestion: str


# Coaching
class CoachingMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(
        min_length=1,
        description="Single chat message in the active UI language",
    )


class CoachingSessionSummary(BaseModel):
    language: Language = Field(
        default=Language.DE,
        description="Language used for the rolling coaching memory",
    )
    learner_needs: list[str] = Field(default_factory=list)
    main_weaknesses: list[str] = Field(default_factory=list)
    explained_criteria: list[str] = Field(default_factory=list)
    rewrite_examples_given: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    open_questions: list[str] = Field(default_factory=list)


class CoachingRequest(BaseModel):
    transcript: str = Field(min_length=1, description="Original examiner transcript")
    duration_seconds: float = Field(ge=0.0, description="Audio duration in seconds")
    evaluation: ResolvedEvaluationResult
    user_message: str = Field(
        min_length=1,
        description="Current user question for the coach",
    )
    conversation: list[CoachingMessage] = Field(default_factory=list)
    session_summary: CoachingSessionSummary | None = None
    output_language: Language = Field(
        default=Language.DE,
        description="Preferred language for the coaching response",
    )


class CoachingCitation(BaseModel):
    source: str
    section: str | None = None
    quote: dict[Language, str] | None = None
    rationale: dict[Language, str] | None = None


class CoachingResponse(BaseModel):
    answer: dict[Language, str]
    citations: list[CoachingCitation] = Field(default_factory=list)
    updated_session_summary: CoachingSessionSummary


class ResolvedCoachingCitation(BaseModel):
    source: str
    section: str | None = None
    quote: str | None = None
    rationale: str | None = None


class ResolvedCoachingResponse(BaseModel):
    output_language: Language
    answer: str
    citations: list[ResolvedCoachingCitation] = Field(default_factory=list)
    updated_session_summary: CoachingSessionSummary


# Documents
class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    chunks_indexed: int


class DocumentDeleteResponse(BaseModel):
    filename: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    indexed_files: list[str]
    total: int


# Health
class HealthResponse(BaseModel):
    status: str
