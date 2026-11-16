from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import NormalizedEmail, PartialUpdateModel


class ClienteCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: NormalizedEmail
    telefone: str | None = Field(default=None, max_length=30)
    empresa: str | None = Field(default=None, max_length=150)


class ClienteUpdate(PartialUpdateModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"telefone", "empresa"})

    nome: str | None = Field(default=None, min_length=2, max_length=150)
    email: NormalizedEmail | None = None
    telefone: str | None = Field(default=None, max_length=30)
    empresa: str | None = Field(default=None, max_length=150)
    ativo: bool | None = None


class ClienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    telefone: str | None
    empresa: str | None
    ativo: bool
    data_criacao: datetime
