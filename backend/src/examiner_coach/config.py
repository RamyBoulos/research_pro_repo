from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the project, four levels up from this file.
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

    # KISSKI / SAIA access
    kisski_api_key: str
    kisski_base_url: str = "https://chat-ai.academiccloud.de/v1"
    kisski_voice_base_url: str = "https://saia.gwdg.de/v1"

    # Model selection
      # Previous default, no longer present in the current SAIA /models response:
    # kisski_llm_model: str = "llama-3.3-70b-instruct"
    kisski_llm_model: str = "meta-llama-3.1-8b-instruct"
    kisski_judge_model: str = "gpt-oss-120b"
    kisski_embedding_model: str = "multilingual-e5-large-instruct"
    kisski_voice_model: str = "whisper-large-v2"

    # Knowledge-base storage
    knowledge_base_dir: Path = ROOT_DIR / "knowledge_base/raw"
    vector_db_dir: Path = ROOT_DIR / "knowledge_base/processed"
    registry_path: Path = ROOT_DIR / "knowledge_base/registry.json"

    # Runtime behavior
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = ""

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def allowed_cors_origins(self) -> list[str]:
        # Development allows local frontend hosts; production must opt in via env.
        if self.is_development:
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


# Single instance imported everywhere
settings = Settings()
