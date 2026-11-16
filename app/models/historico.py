from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.tempo import utcnow

if TYPE_CHECKING:
    from app.models.chamado import Chamado
    from app.models.usuario import Usuario


class HistoricoChamado(Base):
    __tablename__ = "historico_chamados"

    id: Mapped[int] = mapped_column(primary_key=True)
    chamado_id: Mapped[int] = mapped_column(
        ForeignKey("chamados.id", ondelete="CASCADE"), index=True
    )
    # SET NULL: excluir um usuário não apaga a trilha de auditoria.
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), index=True
    )
    acao: Mapped[str] = mapped_column(String(50))
    descricao: Mapped[str] = mapped_column(Text)
    data: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    chamado: Mapped[Chamado] = relationship(back_populates="historicos", lazy="raise")
    usuario: Mapped[Usuario | None] = relationship(back_populates="historicos", lazy="raise")
