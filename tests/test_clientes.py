from httpx import AsyncClient

NOVO = {"nome": "Empresa X", "email": "contato@x.com", "telefone": "11999990000", "empresa": "X Ltda"}


async def test_admin_cria_cliente(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/clientes", headers=admin_headers, json=NOVO)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] and body["ativo"] is True and body["empresa"] == "X Ltda"
    assert (await client.get(f"/clientes/{body['id']}", headers=admin_headers)).status_code == 200


async def test_tecnico_cria_cliente(client: AsyncClient, tecnico_headers: dict):
    assert (await client.post("/clientes", headers=tecnico_headers, json=NOVO)).status_code == 201


async def test_cliente_email_duplicado(client: AsyncClient, admin_headers: dict):
    assert (await client.post("/clientes", headers=admin_headers, json=NOVO)).status_code == 201
    assert (await client.post("/clientes", headers=admin_headers, json=NOVO)).status_code == 409


async def test_cliente_validacao(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/clientes", headers=admin_headers, json={"nome": "X", "email": "invalido"})
    assert resp.status_code == 422


async def test_listagem_paginada_e_busca(client: AsyncClient, admin_headers: dict):
    for i in range(5):
        await client.post("/clientes", headers=admin_headers, json={**NOVO, "email": f"c{i}@x.com", "nome": f"Cliente {i}"})
    p1 = (await client.get("/clientes?page=1&page_size=2", headers=admin_headers)).json()
    assert p1["total"] == 5 and p1["pages"] == 3 and len(p1["items"]) == 2
    p3 = (await client.get("/clientes?page=3&page_size=2", headers=admin_headers)).json()
    assert len(p3["items"]) == 1
    busca = (await client.get("/clientes?busca=Cliente 4", headers=admin_headers)).json()
    assert busca["total"] == 1
    assert (await client.get("/clientes?page_size=1000", headers=admin_headers)).status_code == 422


async def test_atualizar_e_desativar_cliente(client: AsyncClient, admin_headers: dict):
    cid = (await client.post("/clientes", headers=admin_headers, json=NOVO)).json()["id"]
    resp = await client.put(f"/clientes/{cid}", headers=admin_headers, json={"telefone": None, "nome": "Novo Nome"})
    assert resp.status_code == 200 and resp.json()["telefone"] is None and resp.json()["nome"] == "Novo Nome"
    assert (await client.put(f"/clientes/{cid}", headers=admin_headers, json={"nome": None})).status_code == 422
    assert (await client.delete(f"/clientes/{cid}", headers=admin_headers)).status_code == 204
    assert (await client.get(f"/clientes/{cid}", headers=admin_headers)).json()["ativo"] is False
    assert (await client.get("/clientes/9999", headers=admin_headers)).status_code == 404


async def test_tecnicos_crud_admin(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/tecnicos", headers=admin_headers, json={"nome": "Carlos", "email": "carlos@x.com", "especialidade": "Redes"}
    )
    assert resp.status_code == 201
    tid = resp.json()["id"]
    assert (await client.put(f"/tecnicos/{tid}", headers=admin_headers, json={"especialidade": "Servidores"})).json()["especialidade"] == "Servidores"
    assert (await client.delete(f"/tecnicos/{tid}", headers=admin_headers)).status_code == 204
