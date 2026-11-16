from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PerfilUsuario, sa_enum
from app.utils.tempo import utcnow

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.historico import HistoricoChamado
    from app.models.tecnico import Tecnico


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    perfil: Mapped[PerfilUsuario] = mapped_column(
        sa_enum(PerfilUsuario, 20), default=PerfilUsuario.cliente, index=True
    )
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    # lazy="raise": em async, acesso lazy acidental falha de forma explícita
    cliente: Mapped[Cliente | None] = relationship(
        back_populates="usuario", uselist=False, lazy="raise"
    )
    tecnico: Mapped[Tecnico | None] = relationship(
        back_populates="usuario", uselist=False, lazy="raise"
    )
    historicos: Mapped[list[HistoricoChamado]] = relationship(
        back_populates="usuario", lazy="raise"
    )
