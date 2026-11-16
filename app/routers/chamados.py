from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.core.deps import AdminUser, CurrentActor, DbSession
from app.models.enums import PrioridadeChamado, StatusChamado
from app.schemas.chamado import (
    ChamadoCreate,
    ChamadoRead,
    ChamadoStatusUpdate,
    ChamadoUpdate,
    HistoricoRead,
)
from app.schemas.common import Page, Pagination, error_responses, get_pagination, make_page
from app.services import chamado_service

router = APIRouter(
    prefix="/chamados", tags=["Chamados"], responses=error_responses(401, 403)
)

ChamadoId = Annotated[int, Path(ge=1, description="ID do chamado")]


@router.get(
    "",
    response_model=Page[ChamadoRead],
    summary="Lista chamados com filtros e paginação",
    description="Administradores e técnicos veem todos os chamados; clientes veem apenas os seus.",
)
async def listar_chamados(
    actor: CurrentActor,
    db: DbSession,
    pagination: Annotated[Pagination, Depends(get_pagination)],
    status_chamado: Annotated[
        StatusChamado | None, Query(alias="status", description="Filtra por status")
    ] = None,
    prioridade: Annotated[PrioridadeChamado | None, Query(description="Filtra por prioridade")] = None,
    tecnico_id: Annotated[int | None, Query(ge=1, description="Filtra por técnico")] = None,
    cliente_id: Annotated[int | None, Query(ge=1, description="Filtra por cliente")] = None,
) -> dict:
    itens, total = await chamado_service.listar(
        db,
        actor,
        pagination,
        status=status_chamado,
        prioridade=prioridade,
        tecnico_id=tecnico_id,
        cliente_id=cliente_id,
    )
    return make_page(itens, total, pagination)


@router.get(
    "/{chamado_id}",
    response_model=ChamadoRead,
    summary="Consulta um chamado",
    responses=error_responses(404),
)
async def obter_chamado(chamado_id: ChamadoId, actor: CurrentActor, db: DbSession) -> ChamadoRead:
    return ChamadoRead.model_validate(await chamado_service.obter(db, actor, chamado_id))


@router.post(
    "",
    response_model=ChamadoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Abre um chamado",
    description="Gera o protocolo único e registra a criação no histórico. Clientes abrem "
    "em nome próprio; administradores/técnicos devem informar `cliente_id`.",
    responses=error_responses(404, 422),
)
async def criar_chamado(data: ChamadoCreate, actor: CurrentActor, db: DbSession) -> ChamadoRead:
    return ChamadoRead.model_validate(await chamado_service.criar(db, actor, data))


@router.put(
    "/{chamado_id}",
    response_model=ChamadoRead,
    summary="Atualiza dados de um chamado (campos enviados)",
    description="Clientes: apenas título/descrição, enquanto `aberto` ou `aguardando_cliente`. "
    "Técnicos: chamados sem responsável ou atribuídos a si. Administradores: tudo. "
    "Chamados `fechado`/`cancelado` são imutáveis. Para mudar o status use `PATCH .../status`.",
    responses=error_responses(404, 409, 422),
)
async def atualizar_chamado(
    chamado_id: ChamadoId, data: ChamadoUpdate, actor: CurrentActor, db: DbSession
) -> ChamadoRead:
    return ChamadoRead.model_validate(await chamado_service.atualizar(db, actor, chamado_id, data))


@router.patch(
    "/{chamado_id}/status",
    response_model=ChamadoRead,
    summary="Altera o status (inclui resolver, encerrar e cancelar)",
    description="Transições: aberto→em_atendimento|cancelado; em_atendimento→"
    "aguardando_cliente|resolvido|cancelado; aguardando_cliente→em_atendimento|cancelado; "
    "resolvido→fechado|em_atendimento. `fechado`/`cancelado` preenchem `data_fechamento`.",
    responses=error_responses(404, 409, 422),
)
async def alterar_status(
    chamado_id: ChamadoId, data: ChamadoStatusUpdate, actor: CurrentActor, db: DbSession
) -> ChamadoRead:
    return ChamadoRead.model_validate(
        await chamado_service.alterar_status(db, actor, chamado_id, data)
    )


@router.delete(
    "/{chamado_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui um chamado e seu histórico (admin)",
    responses=error_responses(404),
)
async def excluir_chamado(chamado_id: ChamadoId, _: AdminUser, db: DbSession) -> Response:
    await chamado_service.excluir(db, chamado_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{chamado_id}/historico",
    response_model=Page[HistoricoRead],
    summary="Histórico de alterações do chamado",
    responses=error_responses(404),
)
async def historico_chamado(
    chamado_id: ChamadoId,
    actor: CurrentActor,
    db: DbSession,
    pagination: Annotated[Pagination, Depends(get_pagination)],
) -> dict:
    itens, total = await chamado_service.listar_historico(db, actor, chamado_id, pagination)
    return make_page(itens, total, pagination)
