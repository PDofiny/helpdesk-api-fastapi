"""Configurações da aplicação, lidas de variáveis de ambiente / arquivo .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "Help Desk API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    # Obrigatórias: a aplicação não inicia sem elas.
    DATABASE_URL: str
    SECRET_KEY: str = Field(min_length=32)

    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    # Lista separada por vírgulas (ex.: "http://localhost:3000,https://app.exemplo.com")
    CORS_ORIGINS: str = "http://localhost:3000"

    ALLOW_PUBLIC_REGISTRATION: bool = True

    # Usados apenas pelo script `python -m app.scripts.create_admin`
    FIRST_ADMIN_NAME: str = "Administrador"
    FIRST_ADMIN_EMAIL: str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
