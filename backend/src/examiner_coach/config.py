from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the project — two levels up from this file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """
    Central configuration for Examiner Coach.
    All values are loaded from environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Kisski / SAIA ────────────────────────────────────────
    kisski_api_key: str
    kisski_base_url: str = "https://chat-ai.academiccloud.de/v1"
    kisski_voice_base_url: str = "https://saia.gwdg.de/v1"

    # ── Models ───────────────────────────────────────────────
    kisski_llm_model: str = "llama-3.3-70b-instruct"
    kisski_embedding_model: str = "multilingual-e5-large-instruct"
    kisski_voice_model: str = "whisper-large-v2"

    # ── Paths ────────────────────────────────────────────────
    knowledge_base_dir: Path = ROOT_DIR / "knowledge_base/raw"
    vector_db_dir: Path = ROOT_DIR / "knowledge_base/processed"
    registry_path: Path = ROOT_DIR / "knowledge_base/registry.json"

    # ── App ──────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


# Single instance imported everywhere
settings = Settings()