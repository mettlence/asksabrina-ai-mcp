from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Asksabrina AI MCP"
    ENVIRONTMENT: str = "production"
    PORT: int = 8000

    MONGODB_URI: str
    MONGODB_DB_NAME: str = "development"

    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MODEL: str = "gpt-4o-mini"

    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()