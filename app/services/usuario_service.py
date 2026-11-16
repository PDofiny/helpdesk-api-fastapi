"""Regras de negócio de usuários e autenticação."""

import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.security import dummy_hash, hash_password, verify_password
from app.models.cliente import Cliente
from app.models.enums import PerfilUsuario
from app.models.tecnico import Tecnico
from app.models.usuario import Usuario
from app.schemas.common import Pagination
from app.schemas.usuario import UsuarioUpdate
from app.services.pagination import paginate

_MSG_EMAIL = "E-mail já cadastrado"


async def obter_por_email(db: AsyncSession, email: str) -> Usuario | None:
    return await db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


async def obter(db: AsyncSession, usuario_id: int) -> Usuario:
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise NotFoundError("Usuário não encontrado")
    return usuario


async def _garantir_perfil_vinculado(
    db: AsyncSession, usuario: Usuario, *, vincular_existente: bool
) -> None:
    """Cria (ou vincula) o cadastro de Cliente/Técnico correspondente ao perfil do usuário.

    `vincular_existente=False` (cadastro público): NUNCA reaproveita um cadastro já existente
    com o mesmo e-mail, pois e-mails não são verificados e isso daria acesso a dados alheios.
    """
    if usuario.perfil not in (PerfilUsuario.cliente, PerfilUsuario.tecnico):
        return
    modelo = Cliente if usuario.perfil == PerfilUsuario.cliente else Tecnico
    existente = await db.scalar(select(modelo).where(modelo.email == usuario.email))
    if existente is not None:
        if not vincular_existente or existente.usuario_id not in (None, usuario.id):
            raise ConflictError(_MSG_EMAIL)
        existente.usuario_id = usuario.id
        return
    if modelo is Cliente:
        db.add(Cliente(nome=usuario.nome, email=usuario.email, usuario_id=usuario.id))
    else:
        db.add(
            Tecnico(
                nome=usuario.nome,
                email=usuario.email,
                especialidade="Geral",
                usuario_id=usuario.id,
            )
        )


async def criar(
    db: AsyncSession,
    *,
    nome: str,
    email: str,
    senha: str,
    perfil: PerfilUsuario,
    vincular_existente: bool = False,
) -> Usuario:
    if await obter_por_email(db, email):
        raise ConflictError(_MSG_EMAIL)
    senha_hash = await asyncio.to_thread(hash_password, senha)  # CPU-bound: fora do event loop
    usuario = Usuario(nome=nome, email=email, senha_hash=senha_hash, perfil=perfil)
    db.add(usuario)
    try:
        await db.flush()
        await _garantir_perfil_vinculado(db, usuario, vincular_existente=vincular_existente)
        await db.commit()
    except ConflictError:
        await db.rollback()
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(_MSG_EMAIL) from exc
    await db.refresh(usuario)
    return usuario


async def autenticar(db: AsyncSession, email: str, senha: str) -> Usuario:
    usuario = await obter_por_email(db, email)
    hash_alvo = usuario.senha_hash if usuario else dummy_hash()  # tempo constante
    senha_ok = await asyncio.to_thread(verify_password, senha, hash_alvo)
    if usuario is None or not senha_ok:
        raise AuthenticationError("E-mail ou senha incorretos")
    if not usuario.ativo:
        raise PermissionDeniedError("Usuário inativo")
    return usuario


async def listar(
    db: AsyncSession,
    pagination: Pagination,
    *,
    perfil: PerfilUsuario | None = None,
    ativo: bool | None = None,
) -> tuple[list[Usuario], int]:
    stmt = select(Usuario)
    if perfil is not None:
        stmt = stmt.where(Usuario.perfil == perfil)
    if ativo is not None:
        stmt = stmt.where(Usuario.ativo == ativo)
    return await paginate(db, stmt.order_by(Usuario.id), pagination)


async def atualizar(
    db: AsyncSession, usuario_id: int, data: UsuarioUpdate, executor: Usuario
) -> Usuario:
    usuario = await obter(db, usuario_id)
    campos = data.model_dump(exclude_unset=True)

    if usuario.id == executor.id and (
        campos.get("ativo") is False
        or ("perfil" in campos and campos["perfil"] != usuario.perfil)
    ):
        raise BusinessRuleError("Você não pode desativar a si mesmo nem alterar o próprio perfil")

    novo_email = campos.get("email")
    if novo_email and novo_email != usuario.email:
        if await obter_por_email(db, novo_email):
            raise ConflictError(_MSG_EMAIL)

    if "senha" in campos:
        usuario.senha_hash = await asyncio.to_thread(hash_password, campos.pop("senha"))
    perfil_anterior = usuario.perfil
    for campo, valor in campos.items():
        setattr(usuario, campo, valor)

    try:
        if usuario.perfil != perfil_anterior:
            await _garantir_perfil_vinculado(db, usuario, vincular_existente=True)
        await db.commit()
    except ConflictError:
        await db.rollback()
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(_MSG_EMAIL) from exc
    await db.refresh(usuario)
    return usuario


async def desativar(db: AsyncSession, usuario_id: int, executor: Usuario) -> None:
    """Exclusão lógica: preserva histórico e vínculos de auditoria."""
    if usuario_id == executor.id:
        raise BusinessRuleError("Você não pode desativar a si mesmo")
    usuario = await obter(db, usuario_id)
    usuario.ativo = False
    await db.commit()
