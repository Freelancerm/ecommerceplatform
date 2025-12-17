from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration for the notification service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Ecommerce Notification Service"
    DATABASE_URL: str
    REDIS_URL: str
    ELASTICSEARCH_URL: str
    TELEGRAM_BOT_TOKEN: str
    AUTH_SERVICE_URL: str


settings = Settings()
