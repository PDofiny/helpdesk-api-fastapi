import pytest
from httpx import AsyncClient

from tests.conftest import abrir_chamado


@pytest.mark.parametrize(
    ("metodo", "url"),
    [
        ("GET", "/usuarios"),
        ("GET", "/clientes"),
        ("GET", "/tecnicos"),
        ("GET", "/chamados"),
        ("POST", "/chamados"),
        ("GET", "/chamados/1"),
        ("PATCH", "/chamados/1/status"),
        ("GET", "/chamados/1/historico"),
    ],
)
async def test_rotas_privadas_exigem_autenticacao(client: AsyncClient, metodo: str, url: str):
    assert (await client.request(metodo, url)).status_code == 401


async def test_cliente_nao_acessa_rotas_administrativas(client: AsyncClient, cliente_headers: dict):
    assert (await client.get("/usuarios", headers=cliente_headers)).status_code == 403
    assert (await client.get("/clientes", headers=cliente_headers)).status_code == 403
    assert (await client.get("/tecnicos", headers=cliente_headers)).status_code == 403
    novo = {"nome": "Fulano", "email": "f@x.com", "senha": "Senha@12345", "perfil": "administrador"}
    assert (await client.post("/usuarios", headers=cliente_headers, json=novo)).status_code == 403


async def test_tecnico_nao_gerencia_usuarios_nem_tecnicos(client: AsyncClient, tecnico_headers: dict):
    assert (await client.get("/usuarios", headers=tecnico_headers)).status_code == 403
    payload = {"nome": "Novo", "email": "n@x.com", "especialidade": "Redes"}
    assert (await client.post("/tecnicos", headers=tecnico_headers, json=payload)).status_code == 403
    assert (await client.delete("/clientes/1", headers=tecnico_headers)).status_code == 403
    assert (await client.delete("/chamados/1", headers=tecnico_headers)).status_code == 403


async def test_cliente_nao_ve_chamados_de_outro_cliente(client: AsyncClient, cliente_headers: dict, cliente2_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    assert (await client.get(f"/chamados/{ch['id']}", headers=cliente2_headers)).status_code == 404
    assert (await client.get(f"/chamados/{ch['id']}/historico", headers=cliente2_headers)).status_code == 404
    assert (await client.put(f"/chamados/{ch['id']}", headers=cliente2_headers, json={"titulo": "Invasão"})).status_code == 404
    assert (await client.patch(f"/chamados/{ch['id']}/status", headers=cliente2_headers, json={"status": "cancelado"})).status_code == 404
    assert (await client.get("/chamados", headers=cliente2_headers)).json()["total"] == 0
    assert (await client.get("/chamados", headers=cliente_headers)).json()["total"] == 1


async def test_cliente_nao_abre_chamado_em_nome_de_outro(client: AsyncClient, admin_headers: dict, cliente_headers: dict, cliente2_headers: dict):
    outro = (await client.get("/clientes?busca=cli2", headers=admin_headers)).json()["items"][0]["id"]
    resp = await client.post("/chamados", headers=cliente_headers, json={"titulo": "Abc", "descricao": "x", "cliente_id": outro})
    assert resp.status_code == 403
    resp = await client.post("/chamados", headers=cliente_headers, json={"titulo": "Abc", "descricao": "x", "tecnico_id": 1})
    assert resp.status_code == 403


async def test_cliente_nao_altera_prioridade_nem_tecnico_nem_status_indevido(client: AsyncClient, cliente_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    assert (await client.put(f"/chamados/{ch['id']}", headers=cliente_headers, json={"prioridade": "critica"})).status_code == 403
    assert (await client.put(f"/chamados/{ch['id']}", headers=cliente_headers, json={"tecnico_id": 1})).status_code == 403
    assert (await client.patch(f"/chamados/{ch['id']}/status", headers=cliente_headers, json={"status": "em_atendimento"})).status_code == 403  # cliente não inicia atendimento
    assert (await client.delete(f"/chamados/{ch['id']}", headers=cliente_headers)).status_code == 403


async def test_tecnico_nao_mexe_em_chamado_de_outro_tecnico(client: AsyncClient, tecnico_headers: dict, tecnico2_headers: dict, cliente_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    url = f"/chamados/{ch['id']}/status"
    assert (await client.patch(url, headers=tecnico_headers, json={"status": "em_atendimento"})).status_code == 200
    assert (await client.patch(url, headers=tecnico2_headers, json={"status": "resolvido"})).status_code == 403
    assert (await client.put(f"/chamados/{ch['id']}", headers=tecnico2_headers, json={"titulo": "Roubado"})).status_code == 403
    # e não pode atribuir chamados a terceiros
    outro_tid = (await client.get("/auth/me", headers=tecnico2_headers)).json()["id"]  # id de usuário, não de técnico: também inválido
    assert (await client.put(f"/chamados/{ch['id']}", headers=tecnico_headers, json={"tecnico_id": outro_tid + 100})).status_code == 403


async def test_tecnico_sem_assumir_nao_resolve(client: AsyncClient, tecnico_headers: dict, cliente_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    # aberto -> resolvido é transição inválida (409); para "aguardando_cliente" também
    r = await client.patch(f"/chamados/{ch['id']}/status", headers=tecnico_headers, json={"status": "aguardando_cliente"})
    assert r.status_code == 409


async def test_admin_pode_tudo_em_chamados(client: AsyncClient, admin_headers: dict, tecnico_headers: dict, cliente_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    tid = (await client.get("/tecnicos", headers=admin_headers)).json()["items"][0]["id"]
    r = await client.put(f"/chamados/{ch['id']}", headers=admin_headers, json={"tecnico_id": tid})
    assert r.status_code == 200
    r = await client.patch(f"/chamados/{ch['id']}/status", headers=admin_headers, json={"status": "em_atendimento"})
    assert r.status_code == 200
    assert (await client.delete(f"/chamados/{ch['id']}", headers=admin_headers)).status_code == 204


async def test_registro_publico_desabilitado(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ALLOW_PUBLIC_REGISTRATION", False)
    resp = await client.post("/auth/register", json={"nome": "Zé", "email": "ze@x.com", "senha": "Senha@12345"})
    assert resp.status_code == 403


async def test_registro_nao_sequestra_cadastro_de_cliente_existente(client: AsyncClient, admin_headers: dict):
    """Cadastro público com o e-mail de um cliente já cadastrado NÃO pode herdar seus chamados."""
    await client.post("/clientes", headers=admin_headers, json={"nome": "Vítima", "email": "vitima@x.com"})
    resp = await client.post("/auth/register", json={"nome": "Atacante", "email": "vitima@x.com", "senha": "Senha@12345"})
    assert resp.status_code == 409
