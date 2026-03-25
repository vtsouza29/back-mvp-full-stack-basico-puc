from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EventoCreate(BaseModel):
    nome: str = Field(min_length=3, max_length=120, examples=["Python para APIs"])
    descricao: str | None = Field(default=None, max_length=500, examples=["Workshop prático"])
    data_evento: datetime = Field(examples=["2026-04-15T19:00:00"])
    local: str = Field(min_length=3, max_length=120, examples=["Auditório PUC"])
    limite_vagas: int = Field(gt=0, le=5000, examples=[50])


class EventoPublico(BaseModel):
    id: int
    nome: str
    descricao: str | None
    data_evento: datetime
    local: str
    limite_vagas: int
    total_inscritos: int
    vagas_disponiveis: int


class ParticipanteCreate(BaseModel):
    nome: str = Field(min_length=3, max_length=120, examples=["Ana Souza"])
    email: str = Field(examples=["ana.souza@email.com"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_REGEX.match(normalized):
            raise ValueError("Email inválido.")
        return normalized


class InscricaoCreate(BaseModel):
    participante: ParticipanteCreate


class ParticipantePublico(BaseModel):
    id: int
    nome: str
    email: str


class InscricaoPublica(BaseModel):
    id: int
    evento_id: int
    data_inscricao: datetime
    participante: ParticipantePublico


class ParticipanteResumo(BaseModel):
    id: int
    nome: str
    email: str
    total_inscricoes: int


class MensagemResponse(BaseModel):
    mensagem: str

