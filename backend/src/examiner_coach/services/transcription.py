from __future__ import annotations

import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

from examiner_coach.api.schemas import TranscriptionResponse
from examiner_coach.config import settings
from examiner_coach.utils.audio_utils import get_audio_duration_seconds

logger = logging.getLogger(__name__)


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
) -> TranscriptionResponse:
    """
    Transcribe uploaded audio using the configured KISSKI voice endpoint.
    """
    if not audio_bytes:
        raise ValueError("Audio upload was empty.")

    suffix = Path(filename).suffix or ".webm"
    temp_path: Path | None = None

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = Path(temp_file.name)

        duration_seconds = get_audio_duration_seconds(temp_path)

        with temp_path.open("rb") as audio_file:
            response = httpx.post(
                f"{settings.kisski_voice_base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.kisski_api_key}"},
                data={"model": settings.kisski_voice_model},
                files={"file": (filename, audio_file, content_type)},
                timeout=120,
            )
            response.raise_for_status()

        data = response.json()
        transcript = str(data.get("text") or "").strip()
        if not transcript:
            raise ValueError("Transcription returned empty text.")

        return TranscriptionResponse(
            transcript=transcript,
            duration_seconds=duration_seconds,
        )
    except httpx.HTTPError as exc:
        logger.exception("Transcription request failed")
        raise RuntimeError("Transcription request failed.") from exc
    finally:
        if temp_path and temp_path.exists():
            os.unlink(temp_path)
