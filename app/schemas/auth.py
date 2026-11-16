from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import NormalizedEmail, Senha


class RegisterRequest(BaseModel):
    """Cadastro público. O perfil é sempre `cliente` (não é aceito no corpo)."""

    nome: str = Field(min_length=2, max_length=150)
    email: NormalizedEmail
    senha: Senha


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Segundos até a expiração do token")
