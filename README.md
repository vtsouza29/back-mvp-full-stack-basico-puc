# Sistema de Eventos e Inscrições - Back-end

API em Python com FastAPI para gerenciamento de eventos e inscrições, com persistência em SQLite e validação de lotação.

## Tecnologias

- Python 3.11+
- FastAPI
- SQLite (nativo via `sqlite3`)
- Uvicorn

## Estrutura do projeto

```text
.
├── app
│   ├── database.py      # conexão, schema e seed do banco
│   ├── main.py          # rotas da API
│   └── schemas.py       # modelos de requisição/resposta
├── main.py              # ponto de entrada para o uvicorn
├── seed.py              # recria o banco com dados iniciais
└── requirements.txt
```

## Instalação e execução

1. Criar e ativar ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Rodar a API:

```bash
uvicorn main:app --reload
```

4. Acessar a documentação Swagger:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Seed do banco de dados

Na primeira inicialização da API, o banco SQLite é criado automaticamente em `data/eventos.db` e populado com dados de exemplo.

Se quiser resetar e recriar o banco manualmente:

```bash
python seed.py
```

## Rotas implementadas

### Saúde

- `GET /` - confirma que a API está ativa.

### Eventos

- `POST /eventos` - cria evento.
- `GET /eventos` - lista eventos com vagas disponíveis.
- `GET /eventos/{evento_id}` - retorna detalhes de um evento.
- `DELETE /eventos/{evento_id}` - exclui evento.

### Inscrições

- `POST /eventos/{evento_id}/inscricoes` - inscreve participante (com validação de lotação e duplicidade).
- `GET /eventos/{evento_id}/inscricoes` - lista inscritos de um evento.
- `DELETE /eventos/{evento_id}/inscricoes/{inscricao_id}` - cancela inscrição.

### Participantes

- `GET /participantes` - lista participantes e total de inscrições.

## Regras de negócio implementadas

- Um evento possui limite de vagas obrigatório.
- A API bloqueia inscrição quando o evento está lotado (`409 Conflict`).
- A API bloqueia inscrição duplicada do mesmo participante no mesmo evento (`409 Conflict`).
- Emails de participantes são normalizados para minúsculo.
