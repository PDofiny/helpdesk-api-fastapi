# Helpdesk API

API REST para gerenciamento de chamados de suporte técnico (helpdesk), desenvolvida com **FastAPI**.

O projeto nasceu da minha experiência diária em suporte técnico N1: a ideia é modelar, em código, o fluxo real de abertura, acompanhamento e fechamento de chamados.

## Funcionalidades

- Abertura de chamados com título, descrição e prioridade
- Listagem e filtro de chamados
- Consulta de um chamado específico
- Atualização de status (ex.: aberto, em andamento, resolvido)
- Exclusão de chamados
- Documentação interativa gerada automaticamente (Swagger UI)


## Tecnologias

- Python 3
- FastAPI
- Uvicorn
- Pydantic (validação de dados)
- Git e GitHub


## Como executar localmente

### 1. Clonar o repositório

```powershell
git clone https://github.com/PDofiny/helpdesk-api-fastapi.git
cd helpdesk-api-fastapi
```

### 2. Criar e ativar o ambiente virtual

```powershell
python -m venv venv
venv\Scripts\activate
```

No Linux/macOS: `source venv/bin/activate`

### 3. Instalar as dependências

```powershell
pip install -r requirements.txt
```

### 4. Iniciar o servidor

```powershell
uvicorn app.main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`.

## Documentação da API

Com o servidor rodando, acesse:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Endpoints principais

| Método | Rota                | Descrição                    |
|--------|---------------------|------------------------------|
| GET    | `/tickets`          | Lista todos os chamados      |
| GET    | `/tickets/{id}`     | Retorna um chamado           |
| POST   | `/tickets`          | Cria um novo chamado         |
| PUT    | `/tickets/{id}`     | Atualiza um chamado          |
| DELETE | `/tickets/{id}`     | Remove um chamado            |


## Estrutura do projeto

```
helpdesk-api-fastapi/
├── app/
│   ├── main.py
│   └── ...
├── requirements.txt
└── README.md
```


## Próximos passos

- [ ] Autenticação de usuários
- [ ] Testes automatizados com pytest
- [ ] Persistência em banco de dados
- [ ] Deploy em nuvem

## Autor

**Pedro Dofiny**
Rio de Janeiro, Brasil

GitHub: [@PDofiny](https://github.com/PDofiny)
