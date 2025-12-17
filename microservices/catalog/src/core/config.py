from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration for the catalog service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Ecommerce catalog service"
    DATABASE_URL: str
    REDIS_URL: str
    ELASTICSEARCH_URL: str


settings = Settings()
