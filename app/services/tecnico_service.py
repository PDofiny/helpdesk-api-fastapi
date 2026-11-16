from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.tecnico import Tecnico
from app.schemas.common import Pagination
from app.schemas.tecnico import TecnicoCreate, TecnicoUpdate
from app.services.pagination import paginate

_MSG_EMAIL = "Já existe um técnico com este e-mail"


async def obter(db: AsyncSession, tecnico_id: int) -> Tecnico:
    tecnico = await db.get(Tecnico, tecnico_id)
    if tecnico is None:
        raise NotFoundError("Técnico não encontrado")
    return tecnico


async def _email_em_uso(db: AsyncSession, email: str, ignorar_id: int | None = None) -> bool:
    stmt = select(Tecnico.id).where(Tecnico.email == email)
    if ignorar_id is not None:
        stmt = stmt.where(Tecnico.id != ignorar_id)
    return await db.scalar(stmt) is not None


async def listar(
    db: AsyncSession,
    pagination: Pagination,
    *,
    ativo: bool | None = None,
    especialidade: str | None = None,
) -> tuple[list[Tecnico], int]:
    stmt = select(Tecnico)
    if ativo is not None:
        stmt = stmt.where(Tecnico.ativo == ativo)
    if especialidade:
        stmt = stmt.where(Tecnico.especialidade.icontains(especialidade, autoescape=True))
    return await paginate(db, stmt.order_by(Tecnico.nome, Tecnico.id), pagination)


async def criar(db: AsyncSession, data: TecnicoCreate) -> Tecnico:
    if await _email_em_uso(db, data.email):
        raise ConflictError(_MSG_EMAIL)
    tecnico = Tecnico(**data.model_dump())
    db.add(tecnico)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(_MSG_EMAIL) from exc
    await db.refresh(tecnico)
    return tecnico


async def atualizar(db: AsyncSession, tecnico_id: int, data: TecnicoUpdate) -> Tecnico:
    tecnico = await obter(db, tecnico_id)
    campos = data.model_dump(exclude_unset=True)
    if "email" in campos and await _email_em_uso(db, campos["email"], tecnico.id):
        raise ConflictError(_MSG_EMAIL)
    for campo, valor in campos.items():
        setattr(tecnico, campo, valor)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(_MSG_EMAIL) from exc
    await db.refresh(tecnico)
    return tecnico


async def desativar(db: AsyncSession, tecnico_id: int) -> None:
    """Exclusão lógica (técnicos podem ter chamados em andamento)."""
    tecnico = await obter(db, tecnico_id)
    tecnico.ativo = False
    await db.commit()
