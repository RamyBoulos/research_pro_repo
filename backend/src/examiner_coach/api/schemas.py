from enum import Enum

from pydantic import BaseModel, Field


# ── Shared enums ─────────────────────────────────────────────

class Language(str, Enum):
    EN = "en"
    DE = "de"


# ── Audio / Transcription ─────────────────────────────────────

class TranscriptionResponse(BaseModel):
    transcript: str
    duration_seconds: float


# ── Evaluation ───────────────────────────────────────────────

class EvaluationRequest(BaseModel):
    """Input payload for evaluating an examiner feedback transcript."""
    transcript: str = Field(min_length=1, description="Transcript text to evaluate")
    duration_seconds: float = Field(ge=0.0, description="Audio duration in seconds")
    output_language: Language = Field(
        default=Language.EN,
        description="Preferred language for displaying the result",
    )


class CriterionResult(BaseModel):
    """Result for a single STOP feedback criterion."""
    criterion_id: str = Field(description="Unique identifier e.g. 'specific_behavior'")
    label: dict[Language, str] = Field(description="Human-readable label in EN and DE")
    score_percent: float = Field(
        ge=0.0,
        le=100.0,
        description="How strongly the criterion was met, expressed as a percentage",
    )
    comment: dict[Language, str] = Field(description="LLM explanation in EN and DE")
    quote: dict[Language, str] | None = Field(
        default=None,
        description="Relevant quote from transcript, if applicable"
    )


class EvaluationResult(BaseModel):
    """Full STOP radar evaluation returned to the frontend."""
    transcript: str
    duration_seconds: float
    overall_score: float = Field(ge=0.0, le=100.0, description="Percentage 0-100")
    criteria_met: int
    total_criteria: int
    criteria: list[CriterionResult]
    key_suggestion: dict[Language, str] = Field(
        description="Single most important improvement tip in EN and DE"
    )


class ResolvedCriterionResult(BaseModel):
    """Single-language view of a STOP criterion for display or export."""
    criterion_id: str
    label: str
    score_percent: float = Field(
        ge=0.0,
        le=100.0,
        description="How strongly the criterion was met, expressed as a percentage",
    )
    comment: str
    quote: str | None = None


class ResolvedEvaluationResult(BaseModel):
    """Single-language view of an evaluation resolved from the bilingual result."""
    output_language: Language
    transcript: str
    duration_seconds: float
    overall_score: float = Field(ge=0.0, le=100.0, description="Percentage 0-100")
    criteria_met: int
    total_criteria: int
    criteria: list[ResolvedCriterionResult]
    key_suggestion: str


# ── Documents ────────────────────────────────────────────────

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


# ── Health ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
