from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Path, status
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_connection, init_database, seed_database
from app.schemas import (
    EventoCreate,
    EventoPublico,
    InscricaoCreate,
    InscricaoPublica,
    MensagemResponse,
    ParticipantePublico,
    ParticipanteResumo,
)

EVENTO_SELECT_BASE = """
SELECT
    e.id,
    e.nome,
    e.descricao,
    e.data_evento,
    e.local,
    e.limite_vagas,
    COUNT(i.id) AS total_inscritos,
    (e.limite_vagas - COUNT(i.id)) AS vagas_disponiveis
FROM eventos e
LEFT JOIN inscricoes i ON i.evento_id = e.id
"""

EVENTO_GROUP_BY = """
GROUP BY e.id, e.nome, e.descricao, e.data_evento, e.local, e.limite_vagas
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    seed_database()
    yield


app = FastAPI(
    title="Sistema de Eventos e Inscrições",
    version="1.0.0",
    description=(
        "API para gerenciamento de eventos e inscrições com validação de lotação.\n\n"
        "Principais recursos:\n"
        "- Cadastro e consulta de eventos;\n"
        "- Inscrição de participantes;\n"
        "- Validação de limite de vagas;\n"
        "- Cancelamento de inscrição."
    ),
    openapi_tags=[
        {"name": "Saúde", "description": "Rotas utilitárias para checagem da API."},
        {"name": "Eventos", "description": "Operações de criação e consulta de eventos."},
        {"name": "Inscrições", "description": "Fluxo completo de inscrições e cancelamentos."},
        {"name": "Participantes", "description": "Consulta de participantes cadastrados."},
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    connection = create_connection()
    try:
        yield connection
    finally:
        connection.close()


def row_to_evento(row: sqlite3.Row) -> EventoPublico:
    return EventoPublico(
        id=row["id"],
        nome=row["nome"],
        descricao=row["descricao"],
        data_evento=row["data_evento"],
        local=row["local"],
        limite_vagas=row["limite_vagas"],
        total_inscritos=row["total_inscritos"],
        vagas_disponiveis=row["vagas_disponiveis"],
    )


def get_evento_by_id(connection: sqlite3.Connection, evento_id: int) -> EventoPublico | None:
    row = connection.execute(
        f"""
        {EVENTO_SELECT_BASE}
        WHERE e.id = ?
        {EVENTO_GROUP_BY};
        """,
        (evento_id,),
    ).fetchone()
    if not row:
        return None
    return row_to_evento(row)


@app.get(
    "/",
    tags=["Saúde"],
    response_model=MensagemResponse,
    summary="Verificar status da API",
    description="Retorna uma mensagem simples confirmando que a API está em execução.",
)
def healthcheck() -> MensagemResponse:
    return MensagemResponse(mensagem="API de eventos ativa. Consulte /docs para a documentação Swagger.")


@app.post(
    "/eventos",
    tags=["Eventos"],
    response_model=EventoPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Criar evento",
    description="Cria um novo evento com nome, data, local e limite de vagas.",
    responses={
        201: {"description": "Evento criado com sucesso."},
        422: {"description": "Dados inválidos na requisição."},
    },
)
def criar_evento(evento: EventoCreate, db: sqlite3.Connection = Depends(get_db)) -> EventoPublico:
    cursor = db.execute(
        """
        INSERT INTO eventos (nome, descricao, data_evento, local, limite_vagas)
        VALUES (?, ?, ?, ?, ?);
        """,
        (evento.nome, evento.descricao, evento.data_evento.isoformat(), evento.local, evento.limite_vagas),
    )
    db.commit()
    evento_criado = get_evento_by_id(db, cursor.lastrowid)
    if not evento_criado:
        raise HTTPException(status_code=500, detail="Falha ao recuperar evento criado.")
    return evento_criado


@app.get(
    "/eventos",
    tags=["Eventos"],
    response_model=list[EventoPublico],
    summary="Listar eventos",
    description="Lista todos os eventos com total de inscritos e vagas disponíveis.",
)
def listar_eventos(db: sqlite3.Connection = Depends(get_db)) -> list[EventoPublico]:
    rows = db.execute(
        f"""
        {EVENTO_SELECT_BASE}
        {EVENTO_GROUP_BY}
        ORDER BY e.id ASC;
        """
    ).fetchall()
    return [row_to_evento(row) for row in rows]


@app.get(
    "/eventos/{evento_id}",
    tags=["Eventos"],
    response_model=EventoPublico,
    summary="Buscar evento por ID",
    description="Retorna os detalhes de um evento específico.",
    responses={404: {"description": "Evento não encontrado."}},
)
def buscar_evento(
    evento_id: int = Path(gt=0, description="ID do evento"),
    db: sqlite3.Connection = Depends(get_db),
) -> EventoPublico:
    evento = get_evento_by_id(db, evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return evento


@app.delete(
    "/eventos/{evento_id}",
    tags=["Eventos"],
    response_model=MensagemResponse,
    summary="Excluir evento",
    description="Exclui um evento e suas inscrições vinculadas.",
    responses={404: {"description": "Evento não encontrado."}},
)
def deletar_evento(
    evento_id: int = Path(gt=0, description="ID do evento"),
    db: sqlite3.Connection = Depends(get_db),
) -> MensagemResponse:
    evento = db.execute("SELECT id FROM eventos WHERE id = ?;", (evento_id,)).fetchone()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    db.execute("DELETE FROM eventos WHERE id = ?;", (evento_id,))
    db.commit()
    return MensagemResponse(mensagem="Evento excluído com sucesso.")


@app.post(
    "/eventos/{evento_id}/inscricoes",
    tags=["Inscrições"],
    response_model=InscricaoPublica,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrever participante no evento",
    description=(
        "Cria uma inscrição para um participante em um evento.\n\n"
        "Validações aplicadas:\n"
        "- evento precisa existir;\n"
        "- evento não pode estar lotado;\n"
        "- participante não pode se inscrever duas vezes no mesmo evento."
    ),
    responses={
        201: {"description": "Inscrição realizada com sucesso."},
        404: {"description": "Evento não encontrado."},
        409: {"description": "Evento lotado ou participante já inscrito."},
        422: {"description": "Dados inválidos na requisição."},
    },
)
def inscrever_participante(
    payload: InscricaoCreate,
    evento_id: int = Path(gt=0, description="ID do evento"),
    db: sqlite3.Connection = Depends(get_db),
) -> InscricaoPublica:
    evento = get_evento_by_id(db, evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    if evento.total_inscritos >= evento.limite_vagas:
        raise HTTPException(status_code=409, detail="Evento lotado. Não há vagas disponíveis.")

    participante = db.execute(
        "SELECT id, nome, email FROM participantes WHERE lower(email) = ?;",
        (payload.participante.email.lower(),),
    ).fetchone()

    if participante:
        participante_id = participante["id"]
        if participante["nome"] != payload.participante.nome:
            db.execute("UPDATE participantes SET nome = ? WHERE id = ?;", (payload.participante.nome, participante_id))
    else:
        cursor = db.execute(
            "INSERT INTO participantes (nome, email) VALUES (?, ?);",
            (payload.participante.nome, payload.participante.email.lower()),
        )
        participante_id = cursor.lastrowid

    try:
        cursor = db.execute(
            "INSERT INTO inscricoes (evento_id, participante_id) VALUES (?, ?);",
            (evento_id, participante_id),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Participante já inscrito neste evento.") from exc

    row = db.execute(
        """
        SELECT
            i.id,
            i.evento_id,
            i.data_inscricao,
            p.id AS participante_id,
            p.nome AS participante_nome,
            p.email AS participante_email
        FROM inscricoes i
        JOIN participantes p ON p.id = i.participante_id
        WHERE i.id = ?;
        """,
        (cursor.lastrowid,),
    ).fetchone()

    return InscricaoPublica(
        id=row["id"],
        evento_id=row["evento_id"],
        data_inscricao=row["data_inscricao"],
        participante=ParticipantePublico(
            id=row["participante_id"],
            nome=row["participante_nome"],
            email=row["participante_email"],
        ),
    )


@app.get(
    "/eventos/{evento_id}/inscricoes",
    tags=["Inscrições"],
    response_model=list[InscricaoPublica],
    summary="Listar inscritos por evento",
    description="Retorna todos os participantes inscritos em um evento.",
    responses={404: {"description": "Evento não encontrado."}},
)
def listar_inscricoes_evento(
    evento_id: int = Path(gt=0, description="ID do evento"),
    db: sqlite3.Connection = Depends(get_db),
) -> list[InscricaoPublica]:
    evento = get_evento_by_id(db, evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    rows = db.execute(
        """
        SELECT
            i.id,
            i.evento_id,
            i.data_inscricao,
            p.id AS participante_id,
            p.nome AS participante_nome,
            p.email AS participante_email
        FROM inscricoes i
        JOIN participantes p ON p.id = i.participante_id
        WHERE i.evento_id = ?
        ORDER BY i.data_inscricao DESC;
        """,
        (evento_id,),
    ).fetchall()

    return [
        InscricaoPublica(
            id=row["id"],
            evento_id=row["evento_id"],
            data_inscricao=row["data_inscricao"],
            participante=ParticipantePublico(
                id=row["participante_id"],
                nome=row["participante_nome"],
                email=row["participante_email"],
            ),
        )
        for row in rows
    ]


@app.delete(
    "/eventos/{evento_id}/inscricoes/{inscricao_id}",
    tags=["Inscrições"],
    response_model=MensagemResponse,
    summary="Cancelar inscrição",
    description="Cancela a inscrição de um participante em um evento.",
    responses={404: {"description": "Inscrição não encontrada para o evento informado."}},
)
def cancelar_inscricao(
    evento_id: int = Path(gt=0, description="ID do evento"),
    inscricao_id: int = Path(gt=0, description="ID da inscrição"),
    db: sqlite3.Connection = Depends(get_db),
) -> MensagemResponse:
    inscricao = db.execute(
        "SELECT id FROM inscricoes WHERE id = ? AND evento_id = ?;",
        (inscricao_id, evento_id),
    ).fetchone()
    if not inscricao:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada para este evento.")

    db.execute("DELETE FROM inscricoes WHERE id = ?;", (inscricao_id,))
    db.commit()
    return MensagemResponse(mensagem="Inscrição cancelada com sucesso.")


@app.get(
    "/participantes",
    tags=["Participantes"],
    response_model=list[ParticipanteResumo],
    summary="Listar participantes",
    description="Lista participantes cadastrados e o total de inscrições de cada um.",
)
def listar_participantes(db: sqlite3.Connection = Depends(get_db)) -> list[ParticipanteResumo]:
    rows = db.execute(
        """
        SELECT
            p.id,
            p.nome,
            p.email,
            COUNT(i.id) AS total_inscricoes
        FROM participantes p
        LEFT JOIN inscricoes i ON i.participante_id = p.id
        GROUP BY p.id, p.nome, p.email
        ORDER BY p.nome ASC;
        """
    ).fetchall()
    return [
        ParticipanteResumo(
            id=row["id"],
            nome=row["nome"],
            email=row["email"],
            total_inscricoes=row["total_inscricoes"],
        )
        for row in rows
    ]
