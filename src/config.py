from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    PORT: int = 8000

    MONGODB_URI: str
    DB_NAME: str = "development"

    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"

    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"
        extra = "ignore"  # <-- allows extra keys if any

settings = Settings()