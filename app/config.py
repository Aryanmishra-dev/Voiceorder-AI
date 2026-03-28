from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    # Database
    DATABASE_URL: str
    
    # API Keys
    OPENAI_API_KEY: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    
    # Security
    ENABLE_WEBHOOK_VALIDATION: bool = True
    WEBHOOK_TIMEOUT_SECONDS: int = 30
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # time window in seconds
    
    # API Configuration
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_TEMPERATURE: float = 0.7
    LLM_EXTRACTION_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 300
    
    # Application
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"


settings = Settings()
