from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import Pagination


async def paginate(
    db: AsyncSession, stmt: Select[Any], pagination: Pagination
) -> tuple[list[Any], int]:
    """Executa `stmt` paginado e devolve (itens, total sem paginação)."""
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = await db.scalars(stmt.limit(pagination.page_size).offset(pagination.offset))
    return list(rows.all()), total or 0
