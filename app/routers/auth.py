from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import PermissionDeniedError
from app.core.security import create_access_token
from app.models.enums import PerfilUsuario
from app.schemas.auth import RegisterRequest, Token
from app.schemas.common import error_responses
from app.schemas.usuario import UsuarioRead
from app.services import usuario_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/register",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastro público de usuário (perfil cliente)",
    description="Cria a conta e o cadastro de cliente vinculado. O perfil é sempre `cliente`; "
    "contas de técnico/administrador são criadas por um administrador em `POST /usuarios`.",
    responses=error_responses(403, 409),
)
async def register(data: RegisterRequest, db: DbSession) -> UsuarioRead:
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise PermissionDeniedError("O cadastro público está desabilitado")
    usuario = await usuario_service.criar(
        db, nome=data.nome, email=data.email, senha=data.senha, perfil=PerfilUsuario.cliente
    )
    return UsuarioRead.model_validate(usuario)


@router.post(
    "/login",
    response_model=Token,
    summary="Login (OAuth2 password flow)",
    description="Envie `username` (o e-mail) e `password` como **form-data**. "
    "Use o `access_token` no cabeçalho `Authorization: Bearer <token>`.",
    responses=error_responses(401, 403),
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> Token:
    usuario = await usuario_service.autenticar(db, form.username, form.password)
    token, expires_in = create_access_token(usuario.id)
    return Token(access_token=token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=UsuarioRead,
    summary="Dados do usuário autenticado",
    responses=error_responses(401),
)
async def me(usuario: CurrentUser) -> UsuarioRead:
    return UsuarioRead.model_validate(usuario)
