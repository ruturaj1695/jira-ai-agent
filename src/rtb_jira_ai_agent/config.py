from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_env: str = "development"
    log_level: str = "INFO"

    # Company-provided RTB Ollama platform.
    # Keep the server URL configurable; never commit internal credentials.
    llm_provider: str = "ollama"
    ollama_base_url: str | None = None
    llm_model: str = "llama3:8b"
    ollama_embedding_model: str = "qwen3-embedding:latest"

    # Optional cloud fallback for local development only.
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    anthropic_api_key: str | None = None

    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None
    jira_board_id: int | None = None
    jira_story_points_field: str | None = None
    jira_ssl_verify: bool = True
    jira_ca_bundle: str | None = None
    jira_max_results: int = 50
    chroma_persist_directory: str = "./chroma_db"
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "rtb-jira-ai-agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
