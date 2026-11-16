"""Dependências do FastAPI: sessão, usuário autenticado, controle de acesso por perfil."""

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.services.actor import Actor, resolve_actor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> Usuario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        usuario_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credenciais_invalidas from exc

    usuario = await db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:  # desativar um usuário invalida seus tokens
        raise credenciais_invalidas
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*perfis: PerfilUsuario) -> Callable[[Usuario], Awaitable[Usuario]]:
    async def _checar(usuario: CurrentUser) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem permissão para esta operação",
            )
        return usuario

    return _checar


AdminUser = Annotated[Usuario, Depends(require_roles(PerfilUsuario.administrador))]
StaffUser = Annotated[
    Usuario, Depends(require_roles(PerfilUsuario.administrador, PerfilUsuario.tecnico))
]


async def get_actor(usuario: CurrentUser, db: DbSession) -> Actor:
    return await resolve_actor(db, usuario)


CurrentActor = Annotated[Actor, Depends(get_actor)]
