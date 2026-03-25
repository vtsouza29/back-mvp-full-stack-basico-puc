from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "eventos.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    data_evento TEXT NOT NULL,
    local TEXT NOT NULL,
    limite_vagas INTEGER NOT NULL CHECK (limite_vagas > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inscricoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL,
    participante_id INTEGER NOT NULL,
    data_inscricao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evento_id, participante_id),
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
    FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE
);
"""


def create_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_database() -> None:
    with create_connection() as connection:
        connection.executescript(SCHEMA_SQL)
        connection.commit()


def seed_database() -> None:
    with create_connection() as connection:
        total_eventos = connection.execute("SELECT COUNT(*) AS total FROM eventos;").fetchone()["total"]
        if total_eventos > 0:
            return

        eventos_seed = [
            {
                "nome": "Python para APIs",
                "descricao": "Workshop prático de FastAPI e boas práticas de backend.",
                "data_evento": "2026-04-15T19:00:00",
                "local": "Auditório PUC",
                "limite_vagas": 3,
            },
            {
                "nome": "Banco de Dados na Prática",
                "descricao": "Hands-on sobre modelagem relacional com SQLite.",
                "data_evento": "2026-04-20T20:00:00",
                "local": "Laboratório 3",
                "limite_vagas": 4,
            },
            {
                "nome": "Noite de Networking Tech",
                "descricao": "Encontro para troca de experiências com alunos da pós.",
                "data_evento": "2026-04-25T18:30:00",
                "local": "Hall Principal",
                "limite_vagas": 2,
            },
        ]

        participantes_seed = [
            {"nome": "Ana Souza", "email": "ana.souza@email.com"},
            {"nome": "Carlos Lima", "email": "carlos.lima@email.com"},
            {"nome": "Marina Costa", "email": "marina.costa@email.com"},
        ]

        evento_ids: dict[str, int] = {}
        for evento in eventos_seed:
            cursor = connection.execute(
                """
                INSERT INTO eventos (nome, descricao, data_evento, local, limite_vagas)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    evento["nome"],
                    evento["descricao"],
                    evento["data_evento"],
                    evento["local"],
                    evento["limite_vagas"],
                ),
            )
            evento_ids[evento["nome"]] = cursor.lastrowid

        participante_ids: dict[str, int] = {}
        for participante in participantes_seed:
            cursor = connection.execute(
                "INSERT INTO participantes (nome, email) VALUES (?, ?);",
                (participante["nome"], participante["email"]),
            )
            participante_ids[participante["email"]] = cursor.lastrowid

        inscricoes_seed = [
            {"evento": "Python para APIs", "email": "ana.souza@email.com"},
            {"evento": "Python para APIs", "email": "carlos.lima@email.com"},
            {"evento": "Banco de Dados na Prática", "email": "marina.costa@email.com"},
        ]

        for inscricao in inscricoes_seed:
            connection.execute(
                "INSERT INTO inscricoes (evento_id, participante_id) VALUES (?, ?);",
                (evento_ids[inscricao["evento"]], participante_ids[inscricao["email"]]),
            )

        connection.commit()


def reset_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

