"""Cria o primeiro administrador a partir de FIRST_ADMIN_* (idempotente).

Uso: python -m app.scripts.create_admin
"""

import asyncio
import sys

from pydantic import TypeAdapter, ValidationError

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.enums import PerfilUsuario
from app.schemas.common import NormalizedEmail, Senha
from app.services import usuario_service


async def main() -> int:
    if not settings.FIRST_ADMIN_EMAIL or not settings.FIRST_ADMIN_PASSWORD:
        print("Defina FIRST_ADMIN_EMAIL e FIRST_ADMIN_PASSWORD no .env", file=sys.stderr)
        return 1
    try:
        email = TypeAdapter(NormalizedEmail).validate_python(settings.FIRST_ADMIN_EMAIL)
        senha = TypeAdapter(Senha).validate_python(settings.FIRST_ADMIN_PASSWORD)
    except ValidationError as exc:
        print(f"Credenciais do admin inválidas:\n{exc}", file=sys.stderr)
        return 1

    async with SessionLocal() as db:
        if await usuario_service.obter_por_email(db, email):
            print(f"Já existe um usuário com o e-mail {email}; nada a fazer.")
        else:
            await usuario_service.criar(
                db,
                nome=settings.FIRST_ADMIN_NAME,
                email=email,
                senha=senha,
                perfil=PerfilUsuario.administrador,
            )
            print(f"Administrador {email} criado com sucesso.")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
