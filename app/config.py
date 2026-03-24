from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "claude-sonnet-4-6"

    # Database
    database_url: str = "postgresql+asyncpg://agentgw:agentgw@localhost:5432/agentgateway"
    sync_database_url: str = "postgresql://agentgw:agentgw@localhost:5432/agentgateway"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    prompt_cache_ttl: int = 3600

    # Auth
    secret_key: str = "dev-secret-change-in-production"
    api_key_prefix: str = "agw_"

    # Integrations
    github_token: str = ""
    notion_token: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    linear_api_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    audit_log_retention_days: int = 90

    # Rate limiting
    default_rate_limit_rpm: int = 60
    default_rate_limit_tokens_per_day: int = 1_000_000


settings = Settings()
