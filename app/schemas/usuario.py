from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PerfilUsuario
from app.schemas.common import NormalizedEmail, PartialUpdateModel, Senha


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: NormalizedEmail
    senha: Senha
    perfil: PerfilUsuario = PerfilUsuario.cliente


class UsuarioUpdate(PartialUpdateModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    email: NormalizedEmail | None = None
    senha: Senha | None = None
    perfil: PerfilUsuario | None = None
    ativo: bool | None = None


class UsuarioRead(BaseModel):
    """Nunca expõe `senha_hash`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    ativo: bool
    perfil: PerfilUsuario
    data_criacao: datetime
