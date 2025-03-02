import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "Laplace API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/laplace")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "laplace_secret_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672")
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    
    class Config:
        case_sensitive = True

settings = Settings()