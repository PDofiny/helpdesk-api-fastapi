from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.schemas.common import Pagination
from app.services.pagination import paginate

_MSG_EMAIL = "Já existe um cliente com este e-mail"


async def obter(db: AsyncSession, cliente_id: int) -> Cliente:
    cliente = await db.get(Cliente, cliente_id)
    if cliente is None:
        raise NotFoundError("Cliente não encontrado")
    return cliente


async def _email_em_uso(db: AsyncSession, email: str, ignorar_id: int | None = None) -> bool:
    stmt = select(Cliente.id).where(Cliente.email == email)
    if ignorar_id is not None:
        stmt = stmt.where(Cliente.id != ignorar_id)
    return await db.scalar(stmt) is not None


async def listar(
    db: AsyncSession,
    pagination: Pagination,
    *,
    ativo: bool | None = None,
    busca: str | None = None,
) -> tuple[list[Cliente], int]:
    stmt = select(Cliente)
    if ativo is not None:
        stmt = stmt.where(Cliente.ativo == ativo)
    if busca:
        stmt = stmt.where(
            Cliente.nome.icontains(busca, autoescape=True)
            | Cliente.email.icontains(busca, autoescape=True)
            | Cliente.empresa.icontains(busca, autoescape=True)
        )
    return await paginate(db, stmt.order_by(Cliente.nome, Cliente.id), pagination)


async def criar(db: AsyncSession, data: ClienteCreate) -> Cliente:
    if await _email_em_uso(db, data.email):
        raise ConflictError(_MSG_EMAIL)
    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(_MSG_EMAIL) from exc
    await db.refresh(cliente)
    return cliente


async def atualizar(db: AsyncSession, cliente_id: int, data: ClienteUpdate) -> Cliente:
    cliente = await obter(db, cliente_id)
    campos = data.model_dump(exclude_unset=True)
    if "email" in campos and await _email_em_uso(db, campos["email"], cliente.id):
        raise ConflictError(_MSG_EMAIL)
    for campo, valor in campos.items():
        setattr(cliente, campo, valor)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(_MSG_EMAIL) from exc
    await db.refresh(cliente)
    return cliente


async def desativar(db: AsyncSession, cliente_id: int) -> None:
    """Exclusão lógica (clientes possuem chamados vinculados)."""
    cliente = await obter(db, cliente_id)
    cliente.ativo = False
    await db.commit()
