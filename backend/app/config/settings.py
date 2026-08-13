from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/orchestration"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/orchestration"
    # Raw psycopg URL for LangGraph checkpointer (no +driver prefix)
    LANGGRAPH_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/orchestration"

    # LLM
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: str = "google/gemma-4-26b-a4b-it:free"
    OPENROUTER_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Workflow limits
    MAX_WORKFLOW_STEPS: int = 20
    MAX_RETRIES: int = 3
    MAX_REVIEW_CYCLES: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def openrouter_base_url(self) -> str:
        return "https://openrouter.ai/api/v1"


settings = Settings()
