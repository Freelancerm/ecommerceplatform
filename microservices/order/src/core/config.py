from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration for the order service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Ecommerce Order service"
    DATABASE_URL: str
    REDIS_URL: str
    ELASTICSEARCH_URL: str
    INVENTORY_SERVICE_URL: str
    PAYMENT_SERVICE_URL: str
    JWT_SECRET: str
    SECRET_KEY: str


settings = Settings()
