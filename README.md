# Help Desk API

API REST para **gerenciamento de chamados de suporte técnico**, construída com FastAPI, SQLAlchemy 2.0 (async), PostgreSQL e JWT.

## 1. Objetivo

Permitir que clientes abram chamados, que técnicos os atendam e que administradores gerenciem usuários, clientes, técnicos e chamados, com:

* autenticação JWT e controle de acesso por perfil (`administrador`, `tecnico`, `cliente`);
* protocolo único por chamado, máquina de estados para o status e **histórico completo** de alterações;
* filtros e paginação nas listagens; documentação automática (Swagger/ReDoc).

## 2. Tecnologias

Python 3.12 · FastAPI · Uvicorn · SQLAlchemy 2.0 (asyncio + asyncpg) · PostgreSQL 16 · Alembic · Pydantic v2 / pydantic-settings · PyJWT · pwdlib (Argon2id) · pytest + pytest-asyncio + httpx · Docker / Docker Compose.

## 3. Estrutura do projeto

```text
app/
├── main.py                 # cria o FastAPI, CORS, handlers de erro e routers
├── core/
│   ├── config.py           # Settings (variáveis de ambiente)
│   ├── database.py         # engine async, sessão, Base, get_db
│   ├── security.py         # hash de senha (Argon2) e JWT
│   ├── deps.py             # usuário autenticado e controle de acesso por perfil
│   └── exceptions.py       # exceções de domínio -> respostas HTTP
├── models/                 # tabelas (SQLAlchemy): usuario, cliente, tecnico, chamado, historico
├── schemas/                # contratos de entrada/saída (Pydantic)
├── routers/                # camada HTTP (finas): auth, usuarios, clientes, tecnicos, chamados
├── services/               # regras de negócio e acesso ao banco
├── utils/                  # protocolo.py, tempo.py
└── scripts/create_admin.py # cria o primeiro administrador
alembic/                    # migrations (versions/0001_esquema_inicial.py)
tests/                      # testes automatizados (pytest)
Dockerfile · docker-compose.yml · .env.example · requirements*.txt
```

## 4. Configurar o ambiente

Pré-requisitos: Python 3.12+, e Docker (para o PostgreSQL local ou para rodar tudo em containers).

### 5. Virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
```

### 6. Instalar dependências

```bash
pip install -r requirements-dev.txt   # inclui as ferramentas de teste
# (em produção basta requirements.txt)
```

### 7. Configurar o `.env`

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # cole o resultado em SECRET_KEY
```

Preencha também `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` (mín. 8 caracteres, com letra e número). O `.env` está no `.gitignore` — **não o versione**. A aplicação **não inicia** sem `DATABASE_URL` e sem `SECRET_KEY` (mín. 32 caracteres).

### 8. Executar as migrations

Suba um PostgreSQL (o do Compose serve) e aplique o esquema:

```bash
docker compose up -d db
alembic upgrade head
python -m app.scripts.create_admin     # cria o primeiro administrador (idempotente)
```

Para criar novas migrations após alterar os models: `alembic revision --autogenerate -m "descrição"` (revise o arquivo gerado antes de aplicar).

### 9. Iniciar a API

```bash
uvicorn app.main:app --reload
```

API em http://localhost:8000 · health-check em `/health`.

### 10. Executar os testes

```bash
pytest
```

Os testes usam SQLite em memória (aiosqlite), isolado a cada teste — **não precisam de PostgreSQL** nem tocam no seu banco.

### 11. Docker

```bash
cp .env.example .env               # e preencha SECRET_KEY, POSTGRES_PASSWORD, FIRST_ADMIN_*
docker compose up --build          # sobe PostgreSQL + API (aplica as migrations ao iniciar)
docker compose exec api python -m app.scripts.create_admin
```

Se alterar `POSTGRES_PASSWORD` depois do primeiro `up`, remova o volume (`docker compose down -v`) — o Postgres só lê essa variável ao inicializar o volume.

### 12. Swagger / ReDoc

* Swagger UI: http://localhost:8000/docs — clique em **Authorize**, informe e-mail em *username* e a senha em *password*.
* ReDoc: http://localhost:8000/redoc · OpenAPI: `/openapi.json`

### 13. Exemplos de requisições

```bash
# Cadastro público (cria conta + cadastro de cliente)
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"nome":"Maria","email":"maria@exemplo.com","senha":"Senha@12345"}'

# Login (form-data, campo "username" = e-mail)
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d 'username=maria@exemplo.com&password=Senha@12345' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Abrir chamado (cliente abre sempre em nome próprio)
curl -X POST localhost:8000/chamados -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"titulo":"VPN não conecta","descricao":"Erro 809","prioridade":"alta"}'

# Listar com filtros e paginação
curl "localhost:8000/chamados?status=aberto&prioridade=alta&page=1&page_size=20" -H "Authorization: Bearer $TOKEN"

# Alterar status (técnico/admin) — ex.: assumir o chamado
curl -X PATCH localhost:8000/chamados/1/status -H "Authorization: Bearer $ADMIN_OU_TECNICO_TOKEN" \
  -H 'Content-Type: application/json' -d '{"status":"em_atendimento","comentario":"Analisando"}'

# Histórico
curl localhost:8000/chamados/1/historico -H "Authorization: Bearer $TOKEN"
```

Um administrador cria técnicos com `POST /usuarios` e `{"perfil":"tecnico", ...}` (isso cria também o cadastro em `/tecnicos`, vinculado à conta de login).

## Regras de negócio

**Perfis e permissões**

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

**Status** (transições permitidas): `aberto → em_atendimento | cancelado` · `em_atendimento → aguardando_cliente | resolvido | cancelado` · `aguardando_cliente → em_atendimento | cancelado` · `resolvido → fechado | em_atendimento (reabrir)`. `fechado` e `cancelado` são finais, imutáveis e preenchem `data_fechamento`.

**Decisões de projeto**

* `DELETE` em usuários, clientes e técnicos é **exclusão lógica** (`ativo=false`), preservando chamados e histórico. Usuário desativado perde o acesso imediatamente (tokens antigos deixam de valer). `DELETE /chamados/{id}` é físico e remove o histórico (cascade).
* Cadastro público (`/auth/register`) cria **sempre** perfil `cliente` e nunca reaproveita um cadastro de cliente existente com o mesmo e-mail (e-mails não são verificados).
* Os valores de perfil usam `tecnico` (sem acento) para serem seguros em URLs/JSON.
* `PUT` aceita **atualização parcial**: apenas os campos enviados são alterados.
* Cliente e Técnico têm `usuario_id` opcional (campo adicional ao especificado) para ligar a conta de login ao cadastro — necessário para o controle de acesso.
* Paginação: `?page=1&page_size=20` (máx. 100); resposta `{items, total, page, page_size, pages}`.

## Limitações conhecidas / próximos passos

* Sem rate limiting no login (recomendado: proxy reverso ou `slowapi`).
* Sem refresh token / revogação individual de tokens (só expiração e desativação do usuário).
* Alterar e-mail/nome de um usuário não sincroniza o cadastro de cliente/técnico vinculado.
* Sem verificação de e-mail no cadastro público (desative com `ALLOW_PUBLIC_REGISTRATION=false` se necessário).
