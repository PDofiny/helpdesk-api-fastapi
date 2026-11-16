from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PrioridadeChamado, StatusChamado
from app.schemas.common import PartialUpdateModel


class ChamadoCreate(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descricao: str = Field(min_length=1, max_length=10_000)
    prioridade: PrioridadeChamado = PrioridadeChamado.media
    cliente_id: int | None = Field(
        default=None,
        ge=1,
        description="Obrigatório para administradores/técnicos. Ignorado (e proibido "
        "divergir) para clientes, que abrem chamados sempre em nome próprio.",
    )
    tecnico_id: int | None = Field(default=None, ge=1)


class ChamadoUpdate(PartialUpdateModel):
    """Atualização parcial: apenas os campos enviados são alterados."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset({"tecnico_id"})

    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descricao: str | None = Field(default=None, min_length=1, max_length=10_000)
    prioridade: PrioridadeChamado | None = None
    cliente_id: int | None = Field(default=None, ge=1)
    tecnico_id: int | None = Field(default=None, ge=1)


class ChamadoStatusUpdate(BaseModel):
    status: StatusChamado
    comentario: str | None = Field(default=None, max_length=1000)


class ChamadoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocolo: str
    titulo: str
    descricao: str
    prioridade: PrioridadeChamado
    status: StatusChamado
    cliente_id: int
    tecnico_id: int | None
    data_abertura: datetime
    data_atualizacao: datetime
    data_fechamento: datetime | None


class HistoricoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chamado_id: int
    usuario_id: int | None
    acao: str
    descricao: str
    data: datetime
