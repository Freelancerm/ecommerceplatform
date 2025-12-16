from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Ecommerce Order service"
    DATABASE_URL: str
    REDIS_URL: str
    ELASTICSEARCH_URL: str
    INVENTORY_SERVICE_URL: str
    PAYMENT_SERVICE_URL: str
    JWT_SECRET: str
    SECRET_KEY: str


    class Config:
        env_file = ".env"


settings = Settings()
