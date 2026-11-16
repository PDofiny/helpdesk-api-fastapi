"""Quem está executando a operação: usuário + perfis de cliente/técnico vinculados."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.enums import PerfilUsuario
from app.models.tecnico import Tecnico
from app.models.usuario import Usuario


@dataclass(frozen=True, slots=True)
class Actor:
    usuario: Usuario
    cliente_id: int | None = None  # preenchido se perfil == cliente e cadastro ativo
    tecnico_id: int | None = None  # preenchido se perfil == tecnico e cadastro ativo

    @property
    def perfil(self) -> PerfilUsuario:
        return self.usuario.perfil

    @property
    def is_admin(self) -> bool:
        return self.perfil == PerfilUsuario.administrador

    @property
    def is_tecnico(self) -> bool:
        return self.perfil == PerfilUsuario.tecnico

    @property
    def is_cliente(self) -> bool:
        return self.perfil == PerfilUsuario.cliente


async def resolve_actor(db: AsyncSession, usuario: Usuario) -> Actor:
    cliente_id: int | None = None
    tecnico_id: int | None = None
    if usuario.perfil == PerfilUsuario.cliente:
        cliente_id = await db.scalar(
            select(Cliente.id).where(Cliente.usuario_id == usuario.id, Cliente.ativo.is_(True))
        )
    elif usuario.perfil == PerfilUsuario.tecnico:
        tecnico_id = await db.scalar(
            select(Tecnico.id).where(Tecnico.usuario_id == usuario.id, Tecnico.ativo.is_(True))
        )
    return Actor(usuario=usuario, cliente_id=cliente_id, tecnico_id=tecnico_id)
