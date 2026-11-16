from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from tests.conftest import SENHA, login


async def test_register_cria_cliente_sem_expor_hash(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"nome": "Maria", "email": "Maria@Example.com", "senha": SENHA, "perfil": "administrador"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "maria@example.com"  # normalizado
    assert body["perfil"] == "cliente"  # perfil enviado no corpo é ignorado
    assert body["ativo"] is True
    assert "senha" not in body and "senha_hash" not in body


async def test_register_email_duplicado(client: AsyncClient):
    payload = {"nome": "Maria", "email": "maria@example.com", "senha": SENHA}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    assert (await client.post("/auth/register", json=payload)).status_code == 409


@pytest.mark.parametrize("senha", ["curta1", "somenteletras", "12345678"])
async def test_register_senha_fraca(client: AsyncClient, senha: str):
    resp = await client.post(
        "/auth/register", json={"nome": "Maria", "email": "m@example.com", "senha": senha}
    )
    assert resp.status_code == 422


async def test_login_sucesso(client: AsyncClient):
    await client.post("/auth/register", json={"nome": "Ana", "email": "ana@example.com", "senha": SENHA})
    resp = await client.post("/auth/login", data={"username": "ana@example.com", "password": SENHA})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer" and body["access_token"] and body["expires_in"] > 0


async def test_login_senha_errada_e_usuario_inexistente(client: AsyncClient):
    await client.post("/auth/register", json={"nome": "Ana", "email": "ana@example.com", "senha": SENHA})
    r1 = await client.post("/auth/login", data={"username": "ana@example.com", "password": "Errada123"})
    r2 = await client.post("/auth/login", data={"username": "nao@existe.com", "password": SENHA})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()  # mesma mensagem: não revela se o e-mail existe
    assert r1.headers["www-authenticate"] == "Bearer"


async def test_me_com_token_valido(client: AsyncClient, cliente_headers: dict):
    resp = await client.get("/auth/me", headers=cliente_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "cli1@example.com"


async def test_me_sem_token_ou_token_invalido(client: AsyncClient):
    assert (await client.get("/auth/me")).status_code == 401
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer lixo.invalido.token"})
    assert resp.status_code == 401


async def test_token_expirado(client: AsyncClient, cliente_headers: dict):
    me = (await client.get("/auth/me", headers=cliente_headers)).json()
    token, _ = create_access_token(me["id"], expires_delta=timedelta(seconds=-5))
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_usuario_desativado_perde_acesso(client: AsyncClient, admin_headers: dict, cliente_headers: dict):
    me = (await client.get("/auth/me", headers=cliente_headers)).json()
    assert (await client.delete(f"/usuarios/{me['id']}", headers=admin_headers)).status_code == 204
    # token antigo deixa de funcionar e novo login é negado
    assert (await client.get("/auth/me", headers=cliente_headers)).status_code == 401
    resp = await client.post("/auth/login", data={"username": "cli1@example.com", "password": SENHA})
    assert resp.status_code == 403


async def test_admin_cria_usuario_e_perfil_tecnico(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/usuarios",
        headers=admin_headers,
        json={"nome": "Tec", "email": "tec@example.com", "senha": SENHA, "perfil": "tecnico"},
    )
    assert resp.status_code == 201 and resp.json()["perfil"] == "tecnico"
    tecnicos = (await client.get("/tecnicos", headers=admin_headers)).json()
    assert tecnicos["total"] == 1 and tecnicos["items"][0]["email"] == "tec@example.com"
    await login(client, "tec@example.com")


async def test_admin_nao_pode_se_autodesativar(client: AsyncClient, admin_headers: dict):
    me = (await client.get("/auth/me", headers=admin_headers)).json()
    assert (await client.delete(f"/usuarios/{me['id']}", headers=admin_headers)).status_code == 422
    resp = await client.put(f"/usuarios/{me['id']}", headers=admin_headers, json={"ativo": False})
    assert resp.status_code == 422


async def test_atualizar_usuario_exige_ao_menos_um_campo(client: AsyncClient, admin_headers: dict):
    me = (await client.get("/auth/me", headers=admin_headers)).json()
    assert (await client.put(f"/usuarios/{me['id']}", headers=admin_headers, json={})).status_code == 422
