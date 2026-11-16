"""Fixtures: banco SQLite em memória (aiosqlite) isolado por teste + usuários de cada perfil.

As variáveis de ambiente são definidas ANTES de importar a aplicação, para que os testes
nunca toquem no banco real configurado no .env.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "chave-de-teste-com-pelo-menos-32-caracteres-ok"
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_PUBLIC_REGISTRATION"] = "true"

from collections.abc import AsyncIterator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PerfilUsuario, Usuario  # noqa: E402

SENHA = "Senha@12345"


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):  # SQLite ignora FKs (ON DELETE CASCADE) sem este PRAGMA
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker) -> AsyncIterator[AsyncClient]:
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def login(client: AsyncClient, email: str, senha: str = SENHA) -> dict[str, str]:
    resp = await client.post("/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, session_factory: async_sessionmaker) -> dict[str, str]:
    async with session_factory() as db:
        db.add(
            Usuario(
                nome="Admin",
                email="admin@example.com",
                senha_hash=hash_password(SENHA),
                perfil=PerfilUsuario.administrador,
            )
        )
        await db.commit()
    return await login(client, "admin@example.com")


async def criar_tecnico(client: AsyncClient, admin_headers: dict, email: str) -> dict[str, str]:
    resp = await client.post(
        "/usuarios",
        headers=admin_headers,
        json={"nome": "Tecnico Teste", "email": email, "senha": SENHA, "perfil": "tecnico"},
    )
    assert resp.status_code == 201, resp.text
    return await login(client, email)


async def criar_cliente_user(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post(
        "/auth/register", json={"nome": "Cliente Teste", "email": email, "senha": SENHA}
    )
    assert resp.status_code == 201, resp.text
    return await login(client, email)


@pytest_asyncio.fixture
async def tecnico_headers(client: AsyncClient, admin_headers: dict) -> dict[str, str]:
    return await criar_tecnico(client, admin_headers, "tec1@example.com")


@pytest_asyncio.fixture
async def tecnico2_headers(client: AsyncClient, admin_headers: dict) -> dict[str, str]:
    return await criar_tecnico(client, admin_headers, "tec2@example.com")


@pytest_asyncio.fixture
async def cliente_headers(client: AsyncClient) -> dict[str, str]:
    return await criar_cliente_user(client, "cli1@example.com")


@pytest_asyncio.fixture
async def cliente2_headers(client: AsyncClient) -> dict[str, str]:
    return await criar_cliente_user(client, "cli2@example.com")


async def abrir_chamado(client: AsyncClient, headers: dict, **extra) -> dict:
    payload = {"titulo": "Impressora não imprime", "descricao": "Erro ao imprimir", **extra}
    resp = await client.post("/chamados", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()
