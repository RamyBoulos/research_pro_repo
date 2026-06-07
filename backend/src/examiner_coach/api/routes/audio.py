from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from examiner_coach.api.schemas import TranscriptionResponse
from examiner_coach.services.transcription import transcribe_audio_bytes

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
) -> TranscriptionResponse:
    """
    Transcribe an uploaded audio recording via the KISSKI voice endpoint.
    """
    filename = audio.filename or "recording.webm"
    content_type = audio.content_type or "audio/webm"
    audio_bytes = await audio.read()

    logger.info(
        "Transcription request received: filename=%s, content_type=%s, size_bytes=%d",
        filename,
        content_type,
        len(audio_bytes),
    )

    try:
        return transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
        )
    except ValueError as exc:
        logger.error("Transcription request rejected: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during transcription route")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected transcription route error: {exc}",
        ) from exc
