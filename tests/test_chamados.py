from httpx import AsyncClient

from tests.conftest import abrir_chamado


async def _cliente_id(client: AsyncClient, admin_headers: dict, email: str) -> int:
    lista = (await client.get(f"/clientes?busca={email}", headers=admin_headers)).json()
    return lista["items"][0]["id"]


async def _tecnico_id(client: AsyncClient, admin_headers: dict, email: str) -> int:
    lista = (await client.get("/tecnicos", headers=admin_headers)).json()
    return next(t["id"] for t in lista["items"] if t["email"] == email)


async def test_cliente_abre_e_consulta_chamado(client: AsyncClient, cliente_headers: dict, admin_headers: dict):
    ch = await abrir_chamado(client, cliente_headers, prioridade="alta")
    assert ch["protocolo"].startswith("HD-") and ch["status"] == "aberto"
    assert ch["prioridade"] == "alta" and ch["tecnico_id"] is None and ch["data_fechamento"] is None
    assert ch["cliente_id"] == await _cliente_id(client, admin_headers, "cli1@example.com")

    resp = await client.get(f"/chamados/{ch['id']}", headers=cliente_headers)
    assert resp.status_code == 200 and resp.json()["protocolo"] == ch["protocolo"]
    assert (await client.get("/chamados/99999", headers=cliente_headers)).status_code == 404


async def test_protocolos_sao_unicos(client: AsyncClient, cliente_headers: dict):
    protocolos = {(await abrir_chamado(client, cliente_headers))["protocolo"] for _ in range(5)}
    assert len(protocolos) == 5


async def test_staff_abre_chamado_para_cliente(client: AsyncClient, admin_headers: dict, tecnico_headers: dict, cliente_headers: dict):
    cid = await _cliente_id(client, admin_headers, "cli1@example.com")
    ch = await abrir_chamado(client, tecnico_headers, cliente_id=cid)
    assert ch["cliente_id"] == cid
    # staff precisa informar cliente_id
    resp = await client.post("/chamados", headers=admin_headers, json={"titulo": "Sem cliente", "descricao": "x"})
    assert resp.status_code == 422
    resp = await client.post("/chamados", headers=admin_headers, json={"titulo": "Cliente fantasma", "descricao": "x", "cliente_id": 9999})
    assert resp.status_code == 404


async def test_atualizacao_de_chamado(client: AsyncClient, cliente_headers: dict, admin_headers: dict, tecnico_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    resp = await client.put(f"/chamados/{ch['id']}", headers=cliente_headers, json={"titulo": "Título corrigido"})
    assert resp.status_code == 200 and resp.json()["titulo"] == "Título corrigido"
    assert resp.json()["data_atualizacao"] >= ch["data_atualizacao"]

    tid = await _tecnico_id(client, admin_headers, "tec1@example.com")
    resp = await client.put(f"/chamados/{ch['id']}", headers=admin_headers, json={"prioridade": "critica", "tecnico_id": tid})
    assert resp.status_code == 200
    assert resp.json()["prioridade"] == "critica" and resp.json()["tecnico_id"] == tid

    assert (await client.put(f"/chamados/{ch['id']}", headers=admin_headers, json={})).status_code == 422
    assert (await client.put(f"/chamados/{ch['id']}", headers=admin_headers, json={"titulo": None})).status_code == 422
    assert (await client.put(f"/chamados/{ch['id']}", headers=admin_headers, json={"tecnico_id": 9999})).status_code == 404


async def test_fluxo_completo_de_atendimento_e_historico(client: AsyncClient, cliente_headers: dict, tecnico_headers: dict, admin_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    url = f"/chamados/{ch['id']}/status"

    # técnico assume (auto-atribuição)
    r = await client.patch(url, headers=tecnico_headers, json={"status": "em_atendimento"})
    assert r.status_code == 200 and r.json()["status"] == "em_atendimento"
    tid = await _tecnico_id(client, admin_headers, "tec1@example.com")
    assert r.json()["tecnico_id"] == tid

    r = await client.patch(url, headers=tecnico_headers, json={"status": "aguardando_cliente", "comentario": "Envie o log"})
    assert r.status_code == 200
    r = await client.patch(url, headers=cliente_headers, json={"status": "em_atendimento"})  # cliente responde
    assert r.status_code == 200
    r = await client.patch(url, headers=tecnico_headers, json={"status": "resolvido"})
    assert r.status_code == 200 and r.json()["data_fechamento"] is None
    r = await client.patch(url, headers=cliente_headers, json={"status": "fechado"})  # encerramento
    assert r.status_code == 200
    assert r.json()["status"] == "fechado" and r.json()["data_fechamento"] is not None

    # chamado encerrado é imutável
    assert (await client.patch(url, headers=admin_headers, json={"status": "em_atendimento"})).status_code == 409
    assert (await client.put(f"/chamados/{ch['id']}", headers=admin_headers, json={"titulo": "Outro"})).status_code == 409

    hist = (await client.get(f"/chamados/{ch['id']}/historico", headers=cliente_headers)).json()
    acoes = [h["acao"] for h in hist["items"]]
    assert acoes == ["criacao", "atribuicao", "mudanca_status", "mudanca_status", "mudanca_status", "mudanca_status", "mudanca_status"]
    assert any("Envie o log" in h["descricao"] for h in hist["items"])
    assert all(h["usuario_id"] for h in hist["items"])


async def test_transicao_invalida_e_status_repetido(client: AsyncClient, cliente_headers: dict, admin_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    url = f"/chamados/{ch['id']}/status"
    assert (await client.patch(url, headers=admin_headers, json={"status": "resolvido"})).status_code == 409
    assert (await client.patch(url, headers=admin_headers, json={"status": "aberto"})).status_code == 409
    assert (await client.patch(url, headers=admin_headers, json={"status": "inexistente"})).status_code == 422
    # admin não pode iniciar atendimento sem técnico atribuído
    assert (await client.patch(url, headers=admin_headers, json={"status": "em_atendimento"})).status_code == 422


async def test_cancelamento_preenche_data_fechamento(client: AsyncClient, cliente_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    r = await client.patch(f"/chamados/{ch['id']}/status", headers=cliente_headers, json={"status": "cancelado"})
    assert r.status_code == 200 and r.json()["data_fechamento"] is not None


async def test_filtros_e_paginacao(client: AsyncClient, admin_headers: dict, tecnico_headers: dict, cliente_headers: dict, cliente2_headers: dict):
    c1 = await _cliente_id(client, admin_headers, "cli1@example.com")
    c2 = await _cliente_id(client, admin_headers, "cli2@example.com")
    tid = await _tecnico_id(client, admin_headers, "tec1@example.com")

    a = await abrir_chamado(client, cliente_headers, prioridade="alta")
    await abrir_chamado(client, cliente_headers, prioridade="baixa")
    await abrir_chamado(client, cliente2_headers, prioridade="alta")
    await client.patch(f"/chamados/{a['id']}/status", headers=tecnico_headers, json={"status": "em_atendimento"})

    async def total(qs: str) -> int:
        resp = await client.get(f"/chamados?{qs}", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        return resp.json()["total"]

    assert await total("") == 3
    assert await total("status=aberto") == 2
    assert await total("status=em_atendimento") == 1
    assert await total("prioridade=alta") == 2
    assert await total(f"tecnico_id={tid}") == 1
    assert await total(f"cliente_id={c1}") == 2
    assert await total(f"cliente_id={c2}&prioridade=alta") == 1
    assert await total("status=aberto&prioridade=baixa") == 1
    page = (await client.get("/chamados?page=2&page_size=2", headers=admin_headers)).json()
    assert len(page["items"]) == 1 and page["pages"] == 2
    assert (await client.get("/chamados?status=xyz", headers=admin_headers)).status_code == 422


async def test_admin_exclui_chamado_e_historico(client: AsyncClient, cliente_headers: dict, admin_headers: dict):
    ch = await abrir_chamado(client, cliente_headers)
    assert (await client.delete(f"/chamados/{ch['id']}", headers=admin_headers)).status_code == 204
    assert (await client.get(f"/chamados/{ch['id']}", headers=admin_headers)).status_code == 404
    assert (await client.get(f"/chamados/{ch['id']}/historico", headers=admin_headers)).status_code == 404
    assert (await client.delete(f"/chamados/{ch['id']}", headers=admin_headers)).status_code == 404
