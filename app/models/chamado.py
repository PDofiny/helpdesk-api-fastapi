from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PrioridadeChamado, StatusChamado, sa_enum
from app.utils.tempo import utcnow

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.historico import HistoricoChamado
    from app.models.tecnico import Tecnico


class Chamado(Base):
    __tablename__ = "chamados"

    id: Mapped[int] = mapped_column(primary_key=True)
    protocolo: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(Text)
    prioridade: Mapped[PrioridadeChamado] = mapped_column(
        sa_enum(PrioridadeChamado, 20), default=PrioridadeChamado.media, index=True
    )
    status: Mapped[StatusChamado] = mapped_column(
        sa_enum(StatusChamado, 30), default=StatusChamado.aberto, index=True
    )
    # Não é possível apagar um cliente que tenha chamados (RESTRICT);
    # ao apagar um técnico, o chamado volta a ficar sem responsável (SET NULL).
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    tecnico_id: Mapped[int | None] = mapped_column(
        ForeignKey("tecnicos.id", ondelete="SET NULL"), index=True
    )
    data_abertura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
    data_fechamento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cliente: Mapped[Cliente] = relationship(back_populates="chamados", lazy="raise")
    tecnico: Mapped[Tecnico | None] = relationship(back_populates="chamados", lazy="raise")
    historicos: Mapped[list[HistoricoChamado]] = relationship(
        back_populates="chamado",
        cascade="all, delete-orphan",
        passive_deletes=True,  # o ON DELETE CASCADE do banco remove o histórico
        lazy="raise",
    )
