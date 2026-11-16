"""Ponto de entrada da aplicação FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.routers import auth, chamados, clientes, tecnicos, usuarios

DESCRICAO = """
API REST de **gerenciamento de chamados de suporte técnico (Help Desk)**.

* Autenticação JWT (Bearer). Faça login em `POST /auth/login` e use o botão **Authorize**.
* Perfis: `administrador`, `tecnico` e `cliente` — cada rota documenta quem pode acessá-la.
* Listagens paginadas (`page`, `page_size`).
"""

TAGS = [
    {"name": "Autenticação", "description": "Cadastro, login e usuário atual"},
    {"name": "Usuários", "description": "Gestão de contas (somente administradores)"},
    {"name": "Clientes", "description": "Cadastro de clientes"},
    {"name": "Técnicos", "description": "Cadastro de técnicos"},
    {"name": "Chamados", "description": "Abertura, atendimento, status e histórico"},
    {"name": "Saúde", "description": "Verificação de disponibilidade"},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=DESCRICAO,
    openapi_tags=TAGS,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    lifespan=lifespan,
)

_origens = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens,
    allow_credentials="*" not in _origens,  # "*" + credenciais é inválido/inseguro
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(clientes.router)
app.include_router(tecnicos.router)
app.include_router(chamados.router)


@app.get("/health", tags=["Saúde"], summary="Verifica se a API está no ar")
async def health() -> dict[str, str]:
    return {"status": "ok"}
