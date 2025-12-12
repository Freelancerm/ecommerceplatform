from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Ecommerce Notification Service"
    DATABASE_URL: str | None = None
    REDIS_URL: str
    ELASTICSEARCH_URL: str | None = None
    TELEGRAM_BOT_TOKEN: str
    AUTH_SERVICE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()
