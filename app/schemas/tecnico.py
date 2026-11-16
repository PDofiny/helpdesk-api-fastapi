from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import NormalizedEmail, PartialUpdateModel


class TecnicoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: NormalizedEmail
    especialidade: str = Field(min_length=2, max_length=100)


class TecnicoUpdate(PartialUpdateModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    email: NormalizedEmail | None = None
    especialidade: str | None = Field(default=None, min_length=2, max_length=100)
    ativo: bool | None = None


class TecnicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    especialidade: str
    ativo: bool
    data_criacao: datetime
