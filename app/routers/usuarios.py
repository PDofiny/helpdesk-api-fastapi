from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.core.deps import AdminUser, DbSession, require_roles
from app.models.enums import PerfilUsuario
from app.schemas.common import Page, Pagination, error_responses, get_pagination, make_page
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.services import usuario_service

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"],
    dependencies=[Depends(require_roles(PerfilUsuario.administrador))],
    responses=error_responses(401, 403),
)

UsuarioId = Annotated[int, Path(ge=1, description="ID do usuário")]


@router.get("", response_model=Page[UsuarioRead], summary="Lista usuários (admin)")
async def listar_usuarios(
    db: DbSession,
    pagination: Annotated[Pagination, Depends(get_pagination)],
    perfil: Annotated[PerfilUsuario | None, Query(description="Filtra por perfil")] = None,
    ativo: Annotated[bool | None, Query(description="Filtra por situação")] = None,
) -> dict:
    itens, total = await usuario_service.listar(db, pagination, perfil=perfil, ativo=ativo)
    return make_page(itens, total, pagination)


@router.get(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Obtém um usuário (admin)",
    responses=error_responses(404),
)
async def obter_usuario(usuario_id: UsuarioId, db: DbSession) -> UsuarioRead:
    return UsuarioRead.model_validate(await usuario_service.obter(db, usuario_id))


@router.post(
    "",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um usuário com qualquer perfil (admin)",
    description="Para perfis `cliente` e `tecnico`, o cadastro correspondente é criado ou, "
    "se já existir com o mesmo e-mail e sem conta, vinculado.",
    responses=error_responses(409),
)
async def criar_usuario(data: UsuarioCreate, db: DbSession) -> UsuarioRead:
    usuario = await usuario_service.criar(
        db,
        nome=data.nome,
        email=data.email,
        senha=data.senha,
        perfil=data.perfil,
        vincular_existente=True,
    )
    return UsuarioRead.model_validate(usuario)


@router.put(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Atualiza um usuário (admin; campos enviados)",
    responses=error_responses(404, 409, 422),
)
async def atualizar_usuario(
    usuario_id: UsuarioId, data: UsuarioUpdate, db: DbSession, admin: AdminUser
) -> UsuarioRead:
    usuario = await usuario_service.atualizar(db, usuario_id, data, admin)
    return UsuarioRead.model_validate(usuario)


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa um usuário (exclusão lógica, admin)",
    responses=error_responses(404, 422),
)
async def desativar_usuario(usuario_id: UsuarioId, db: DbSession, admin: AdminUser) -> Response:
    await usuario_service.desativar(db, usuario_id, admin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
