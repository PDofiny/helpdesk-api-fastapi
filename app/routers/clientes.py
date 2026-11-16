from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.core.deps import AdminUser, DbSession, StaffUser
from app.schemas.cliente import ClienteCreate, ClienteRead, ClienteUpdate
from app.schemas.common import Page, Pagination, error_responses, get_pagination, make_page
from app.services import cliente_service

router = APIRouter(
    prefix="/clientes", tags=["Clientes"], responses=error_responses(401, 403)
)

ClienteId = Annotated[int, Path(ge=1, description="ID do cliente")]


@router.get("", response_model=Page[ClienteRead], summary="Lista clientes (admin/técnico)")
async def listar_clientes(
    _: StaffUser,
    db: DbSession,
    pagination: Annotated[Pagination, Depends(get_pagination)],
    ativo: Annotated[bool | None, Query()] = None,
    busca: Annotated[
        str | None, Query(max_length=100, description="Busca em nome, e-mail e empresa")
    ] = None,
) -> dict:
    itens, total = await cliente_service.listar(db, pagination, ativo=ativo, busca=busca)
    return make_page(itens, total, pagination)


@router.get(
    "/{cliente_id}",
    response_model=ClienteRead,
    summary="Obtém um cliente (admin/técnico)",
    responses=error_responses(404),
)
async def obter_cliente(cliente_id: ClienteId, _: StaffUser, db: DbSession) -> ClienteRead:
    return ClienteRead.model_validate(await cliente_service.obter(db, cliente_id))


@router.post(
    "",
    response_model=ClienteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um cliente (admin/técnico)",
    responses=error_responses(409),
)
async def criar_cliente(data: ClienteCreate, _: StaffUser, db: DbSession) -> ClienteRead:
    return ClienteRead.model_validate(await cliente_service.criar(db, data))


@router.put(
    "/{cliente_id}",
    response_model=ClienteRead,
    summary="Atualiza um cliente (admin/técnico; campos enviados)",
    responses=error_responses(404, 409),
)
async def atualizar_cliente(
    cliente_id: ClienteId, data: ClienteUpdate, _: StaffUser, db: DbSession
) -> ClienteRead:
    return ClienteRead.model_validate(await cliente_service.atualizar(db, cliente_id, data))


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa um cliente (exclusão lógica, admin)",
    responses=error_responses(404),
)
async def desativar_cliente(cliente_id: ClienteId, _: AdminUser, db: DbSession) -> Response:
    await cliente_service.desativar(db, cliente_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
