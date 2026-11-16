# Help Desk API

API REST para **gerenciamento de chamados de suporte técnico**, construída com **FastAPI**, **SQLAlchemy 2.0 (async)**, **PostgreSQL** e **autenticação JWT**.

O projeto nasceu da minha rotina em suporte técnico N1: ele modela, em código, o fluxo real de um service desk, desde a abertura do chamado pelo cliente até o atendimento, a resolução e o fechamento, com histórico completo de tudo o que aconteceu.

## Funcionalidades

- Autenticação JWT e controle de acesso por perfil: `administrador`, `tecnico` e `cliente`
- Protocolo único por chamado e **máquina de estados** para o status (só transições válidas)
- **Histórico completo** de cada chamado (criação, atualização, atribuição e mudança de status)
- Listagens com **filtros e paginação** (status, prioridade, técnico, cliente)
- Exclusão lógica de usuários, clientes e técnicos, preservando chamados e histórico
- Documentação interativa automática (Swagger UI e ReDoc)
- Migrations com Alembic, testes automatizados e execução com Docker Compose

## Tecnologias

Python 3.12 · FastAPI · Uvicorn · SQLAlchemy 2.0 (asyncio + asyncpg) · PostgreSQL 16 · Alembic · Pydantic v2 / pydantic-settings · PyJWT · pwdlib (Argon2id) · pytest + pytest-asyncio + httpx · Docker / Docker Compose

## Estrutura do projeto

```text
app/
├── main.py                 # cria o FastAPI, CORS, handlers de erro e routers
├── core/
│   ├── config.py           # Settings (variáveis de ambiente)
│   ├── database.py         # engine async, sessão, Base, get_db
│   ├── security.py         # hash de senha (Argon2) e JWT
│   ├── deps.py             # usuário autenticado e controle de acesso por perfil
│   └── exceptions.py       # exceções de domínio -> respostas HTTP
├── models/                 # tabelas: usuario, cliente, tecnico, chamado, historico
├── schemas/                # contratos de entrada/saída (Pydantic)
├── routers/                # camada HTTP: auth, usuarios, clientes, tecnicos, chamados
├── services/               # regras de negócio e acesso ao banco
├── utils/                  # protocolo.py, tempo.py
└── scripts/create_admin.py # cria o primeiro administrador
alembic/                    # migrations
tests/                      # testes automatizados (pytest)
```

A aplicação é dividida em camadas: os **routers** cuidam só do HTTP, os **services** concentram as regras de negócio e os **models/schemas** separam persistência de contrato da API.

## Como executar

### Opção 1: Docker (mais rápido)

```bash
git clone https://github.com/PDofiny/helpdesk-api-fastapi.git
cd helpdesk-api-fastapi

cp .env.example .env        # preencha SECRET_KEY, POSTGRES_PASSWORD e FIRST_ADMIN_PASSWORD
docker compose up --build   # sobe PostgreSQL + API (aplica as migrations ao iniciar)
docker compose exec api python -m app.scripts.create_admin
```

> No PowerShell, use `Copy-Item .env.example .env` no lugar do `cp`.

Se alterar `POSTGRES_PASSWORD` depois do primeiro `up`, remova o volume com `docker compose down -v`, pois o Postgres só lê essa variável ao inicializar o volume.

### Opção 2: Ambiente local

Pré-requisitos: Python 3.12+ e Docker (para o PostgreSQL).

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # cole o resultado em SECRET_KEY

docker compose up -d db
alembic upgrade head
python -m app.scripts.create_admin     # cria o primeiro administrador (idempotente)

uvicorn app.main:app --reload
```

A API fica em http://localhost:8000 e o health-check em `/health`.

### Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | **Obrigatória.** URL de conexão (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | **Obrigatória**, mínimo de 32 caracteres. Chave de assinatura do JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token (padrão: 30) |
| `CORS_ORIGINS` | Origens permitidas, separadas por vírgula |
| `ALLOW_PUBLIC_REGISTRATION` | Habilita `POST /auth/register` (padrão: `true`) |
| `FIRST_ADMIN_NAME` / `EMAIL` / `PASSWORD` | Dados do primeiro administrador |

O arquivo `.env` está no `.gitignore`. **Nunca o versione.**

## Documentação interativa

- Swagger UI: http://localhost:8000/docs (clique em **Authorize**, informe o e-mail em *username* e a senha em *password*)
- ReDoc: http://localhost:8000/redoc
- OpenAPI: `/openapi.json`

## Endpoints

| Recurso | Rotas |
|---|---|
| **Autenticação** | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` |
| **Usuários** | `GET /usuarios` · `GET /usuarios/{id}` · `POST /usuarios` · `PUT /usuarios/{id}` · `DELETE /usuarios/{id}` |
| **Clientes** | `GET /clientes` · `GET /clientes/{id}` · `POST /clientes` · `PUT /clientes/{id}` · `DELETE /clientes/{id}` |
| **Técnicos** | `GET /tecnicos` · `GET /tecnicos/{id}` · `POST /tecnicos` · `PUT /tecnicos/{id}` · `DELETE /tecnicos/{id}` |
| **Chamados** | `GET /chamados` · `GET /chamados/{id}` · `POST /chamados` · `PUT /chamados/{id}` · `PATCH /chamados/{id}/status` · `DELETE /chamados/{id}` · `GET /chamados/{id}/historico` |
| **Saúde** | `GET /health` |

### Exemplos de requisições

```bash
# Cadastro público (cria conta + cadastro de cliente)
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"nome":"Maria","email":"maria@exemplo.com","senha":"Senha@12345"}'

# Login (form-data, campo "username" = e-mail)
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d 'username=maria@exemplo.com&password=Senha@12345' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Abrir chamado
curl -X POST localhost:8000/chamados -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"titulo":"VPN não conecta","descricao":"Erro 809","prioridade":"alta"}'

# Listar com filtros e paginação
curl "localhost:8000/chamados?status=aberto&prioridade=alta&page=1&page_size=20" -H "Authorization: Bearer $TOKEN"

# Alterar status (técnico/admin): assumir o chamado
curl -X PATCH localhost:8000/chamados/1/status -H "Authorization: Bearer $ADMIN_OU_TECNICO_TOKEN" \
  -H 'Content-Type: application/json' -d '{"status":"em_atendimento","comentario":"Analisando"}'

# Histórico do chamado
curl localhost:8000/chamados/1/historico -H "Authorization: Bearer $TOKEN"
```

Um administrador cria técnicos com `POST /usuarios` e `{"perfil":"tecnico", ...}`, o que também cria o cadastro em `/tecnicos`, vinculado à conta de login.

## Regras de negócio

### Perfis e permissões

| Recurso | administrador | tecnico | cliente |
|---|---|---|---|
| `/usuarios` | tudo | — | — |
| `/clientes` | tudo | listar, ver, criar, editar | — |
| `/tecnicos` | tudo | listar, ver | — |
| `/chamados` (listar/ver/histórico) | todos | todos | somente os próprios |
| Abrir chamado | para qualquer cliente | para qualquer cliente | em nome próprio |
| Editar chamado (`PUT`) | tudo | sem responsável ou atribuídos a si | só título/descrição, enquanto `aberto`/`aguardando_cliente` |
| Alterar status | qualquer transição válida | se for o responsável (ou assume um chamado livre) | cancelar, fechar `resolvido`, retomar |
| Excluir chamado | ✔ | — | — |

### Ciclo de vida do chamado

Prioridades: `baixa`, `media`, `alta`, `critica`.

```text
aberto              → em_atendimento | cancelado
em_atendimento      → aguardando_cliente | resolvido | cancelado
aguardando_cliente  → em_atendimento | cancelado
resolvido           → fechado | em_atendimento (reabrir)
fechado, cancelado  → estados finais (imutáveis; preenchem data_fechamento)
```

### Decisões de projeto

- `DELETE` em usuários, clientes e técnicos é **exclusão lógica** (`ativo=false`). Usuário desativado perde o acesso imediatamente, inclusive com tokens antigos. `DELETE /chamados/{id}` é físico e remove o histórico (cascade).
- O cadastro público cria **sempre** perfil `cliente` e nunca reaproveita um cadastro existente com o mesmo e-mail, já que e-mails não são verificados.
- `PUT` aceita **atualização parcial**: só os campos enviados são alterados.
- Senhas usam hash **Argon2id**; os enums são persistidos como `VARCHAR`, o que evita `ALTER TYPE` nas migrations.
- Paginação: `?page=1&page_size=20` (máx. 100), com resposta `{items, total, page, page_size, pages}`.

## Testes

```bash
pytest
```

São **39 testes** (autenticação, clientes, chamados e permissões por perfil). Eles usam SQLite em memória (aiosqlite), isolado a cada teste, então **não precisam de PostgreSQL** nem tocam no seu banco.

Para criar novas migrations após alterar os models: `alembic revision --autogenerate -m "descrição"` (revise o arquivo gerado antes de aplicar).

## Limitações conhecidas e próximos passos

- [ ] Rate limiting no login (ex.: proxy reverso ou `slowapi`)
- [ ] Refresh token e revogação individual de tokens
- [ ] Sincronizar nome/e-mail do usuário com o cadastro de cliente/técnico vinculado
- [ ] Verificação de e-mail no cadastro público (hoje dá para desativá-lo com `ALLOW_PUBLIC_REGISTRATION=false`)
- [ ] Pipeline de CI para rodar os testes a cada push

## Autor

**Pedro Dofiny**, Rio de Janeiro, Brasil
GitHub: [@PDofiny](https://github.com/PDofiny)
