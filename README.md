# Sistema de Agendamento DSL

Aplicacao Flask para gerenciamento e agendamento de entregas, com login administrativo, login de RCA, dashboard, relatorios, PWA basico e integracao com Oracle, Redis e API de WhatsApp.

## Estrutura

```text
.
|-- app.py                         # Inicializacao Flask, CSRF e rate limit
|-- routes.py                      # Rotas web e APIs
|-- auth.py                        # Login, sessoes e permissoes
|-- database.py                    # Consultas e cache Redis
|-- database_edit_agendamento.py   # Edicao de agendamentos
|-- charts.py                      # Dados/graficos do dashboard
|-- enviarwpp.py                   # Envio de WhatsApp
|-- config.py                      # Configuracoes via ambiente
|-- templates/                     # Telas HTML
|-- static/                        # CSS, JS, manifest e service worker
|-- scripts/indices_oracle.sql     # Sugestoes de indices Oracle
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
```

## Configuracao

Crie um arquivo `.env` local com base no `.env.example`:

```env
FLASK_SECRET_KEY=troque_esta_chave
FLASK_HOST=0.0.0.0
FLASK_PORT=6000
FLASK_DEBUG=False

DB_USER=usuario_oracle
DB_PASSWORD=senha_oracle
DB_DSN=host:porta/service

API_URL=https://api.exemplo.com
API_TOKEN=token_whatsapp
NUMERO_ADMIN=5500000000000

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

## Execucao Local

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

A aplicacao sobe por padrao em `http://localhost:6000`.

## Docker

```bash
docker compose up --build
```

O `docker-compose.yml` usa o `.env` local em tempo de execucao e tambem inicia Redis.

## Observacoes

- O arquivo `.env` nao deve ser versionado.
- A pasta `bkp/` e arquivos `.bak` nao fazem parte da aplicacao.
- A rota `/atualizar-telefone` referencia `templates/atualizar_telefone.html`, mas esse template nao existe no repositorio atual.
