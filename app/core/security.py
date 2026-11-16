"""Hash de senhas (Argon2 via pwdlib) e tokens JWT (PyJWT)."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_hasher = PasswordHash.recommended()  # Argon2id


def hash_password(senha: str) -> str:
    return _hasher.hash(senha)


def verify_password(senha: str, senha_hash: str) -> bool:
    try:
        return _hasher.verify(senha, senha_hash)
    except Exception:  # hash malformado/desconhecido nunca deve virar 500
        return False


@lru_cache
def dummy_hash() -> str:
    """Hash usado quando o e-mail não existe, para igualar o tempo de resposta do login."""
    return _hasher.hash("senha-descartavel-anti-timing")


def create_access_token(
    subject: int | str, expires_delta: timedelta | None = None
) -> tuple[str, int]:
    """Gera um JWT. Retorna (token, segundos_até_expirar)."""
    agora = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(subject), "iat": agora, "exp": agora + delta}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, int(delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida assinatura e expiração. Lança jwt.PyJWTError se inválido."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
