from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "CodeAtlas"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server Bindings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./codeatlas.db"

    # Redis (Optional in local mode, used for distributed workers)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Ingestion & Sandboxing Guardrails
    WORKSPACE_ROOT: Path = Path("./sandbox/workspaces")
    MAX_REPO_SIZE_MB: int = 250
    MAX_FILES_PER_REPO: int = 10000
    GIT_CLONE_TIMEOUT_SECONDS: int = 60
    ANALYSIS_TIMEOUT_SECONDS: int = 300

    # AI / LLM Configuration
    LLM_PROVIDER: str = "mock"  # mock, openai, gemini
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
