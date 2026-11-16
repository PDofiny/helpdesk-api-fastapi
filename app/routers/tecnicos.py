from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.core.deps import AdminUser, DbSession, StaffUser
from app.schemas.common import Page, Pagination, error_responses, get_pagination, make_page
from app.schemas.tecnico import TecnicoCreate, TecnicoRead, TecnicoUpdate
from app.services import tecnico_service

router = APIRouter(
    prefix="/tecnicos", tags=["Técnicos"], responses=error_responses(401, 403)
)

TecnicoId = Annotated[int, Path(ge=1, description="ID do técnico")]


@router.get("", response_model=Page[TecnicoRead], summary="Lista técnicos (admin/técnico)")
async def listar_tecnicos(
    _: StaffUser,
    db: DbSession,
    pagination: Annotated[Pagination, Depends(get_pagination)],
    ativo: Annotated[bool | None, Query()] = None,
    especialidade: Annotated[str | None, Query(max_length=100)] = None,
) -> dict:
    itens, total = await tecnico_service.listar(
        db, pagination, ativo=ativo, especialidade=especialidade
    )
    return make_page(itens, total, pagination)


@router.get(
    "/{tecnico_id}",
    response_model=TecnicoRead,
    summary="Obtém um técnico (admin/técnico)",
    responses=error_responses(404),
)
async def obter_tecnico(tecnico_id: TecnicoId, _: StaffUser, db: DbSession) -> TecnicoRead:
    return TecnicoRead.model_validate(await tecnico_service.obter(db, tecnico_id))


@router.post(
    "",
    response_model=TecnicoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um técnico (admin)",
    responses=error_responses(409),
)
async def criar_tecnico(data: TecnicoCreate, _: AdminUser, db: DbSession) -> TecnicoRead:
    return TecnicoRead.model_validate(await tecnico_service.criar(db, data))


@router.put(
    "/{tecnico_id}",
    response_model=TecnicoRead,
    summary="Atualiza um técnico (admin; campos enviados)",
    responses=error_responses(404, 409),
)
async def atualizar_tecnico(
    tecnico_id: TecnicoId, data: TecnicoUpdate, _: AdminUser, db: DbSession
) -> TecnicoRead:
    return TecnicoRead.model_validate(await tecnico_service.atualizar(db, tecnico_id, data))


@router.delete(
    "/{tecnico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa um técnico (exclusão lógica, admin)",
    responses=error_responses(404),
)
async def desativar_tecnico(tecnico_id: TecnicoId, _: AdminUser, db: DbSession) -> Response:
    await tecnico_service.desativar(db, tecnico_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
