from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str

    # Segurança
    SECRET_KEY: str
    ALGORITHM:  str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480   # 8 horas

    # Ambiente
    ENVIRONMENT: str = "development"         # development | production

    # CORS (produção — separar por vírgula)
    ALLOWED_ORIGINS: Optional[str] = None

    # Anthropic (módulo 06 — análise IA opcional)
    ANTHROPIC_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
