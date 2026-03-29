from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str

    # External API keys
    OPENAI_API_KEY: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str

    # Admin authentication (required for dashboard and order APIs)
    ADMIN_API_KEY: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Security
    ENABLE_WEBHOOK_VALIDATION: bool = True
    WEBHOOK_TIMEOUT_SECONDS: int = 30
    CORS_ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"
    ENABLE_HSTS: bool = False
    LOG_PII: bool = False

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_IDENTIFIERS: int = 10000

    # LLM configuration
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_TEMPERATURE: float = 0.7
    LLM_EXTRACTION_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 300

    # Application
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated env values."""
        return [item.strip() for item in self.CORS_ALLOWED_ORIGINS.split(",") if item.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        """Parse trusted hosts from comma-separated env values."""
        return [item.strip() for item in self.TRUSTED_HOSTS.split(",") if item.strip()]


settings = Settings()
