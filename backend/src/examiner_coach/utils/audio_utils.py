from __future__ import annotations

import json
import subprocess
from pathlib import Path


def get_audio_duration_seconds(file_path: Path) -> float:
    """
    Read audio duration with ffprobe.

    Returns 0.0 if the duration cannot be determined reliably.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(file_path),
            ],
            capture_output=True,
            check=True,
            text=True,
        )
        data = json.loads(result.stdout or "{}")
        duration_raw = data.get("format", {}).get("duration")
        if duration_raw is None:
            return 0.0
        return max(0.0, round(float(duration_raw), 3))
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        return 0.0
