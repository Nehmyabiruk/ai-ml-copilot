from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AI/ML Engineering Copilot"
    app_env: str = "development"

    # Database
    database_url: str

    # LLM
    llm_api_key: str
    llm_model: str
    embedding_model: str

    # Hugging Face / OpenRouter
    hf_token: str | None = None
    openrouter_api_key: str
    openrouter_model: str = "openrouter/free"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:4173,http://localhost:5174,http://localhost:5175"


settings = Settings()