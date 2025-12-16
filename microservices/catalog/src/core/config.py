from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Ecommerce catalog service"
    DATABASE_URL: str
    REDIS_URL: str
    ELASTICSEARCH_URL: str

    class Config:
        env_file = ".env"


settings = Settings()
