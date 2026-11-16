from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.tempo import utcnow

if TYPE_CHECKING:
    from app.models.chamado import Chamado
    from app.models.usuario import Usuario


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    telefone: Mapped[str | None] = mapped_column(String(30))
    empresa: Mapped[str | None] = mapped_column(String(150))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    # Vínculo opcional com a conta de login (usuário de perfil "cliente").
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), unique=True
    )

    usuario: Mapped[Usuario | None] = relationship(back_populates="cliente", lazy="raise")
    chamados: Mapped[list[Chamado]] = relationship(back_populates="cliente", lazy="raise")
