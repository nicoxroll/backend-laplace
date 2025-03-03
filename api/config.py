import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "Laplace API"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/laplace"
    SECRET_KEY: str = "your-secret-key"  # Cambia esto por una clave segura real
    ALGORITHM: str = "HS256"  # Añadir algoritmo JWT faltante
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672"
    WEAVIATE_URL: str = "http://localhost:8080"

    # Configuración actualizada para Pydantic v2
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()