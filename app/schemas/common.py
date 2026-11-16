"""Tipos e utilitários compartilhados pelos schemas: paginação, e-mail/senha, PATCH parcial."""

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, Generic, Self, TypeVar

from fastapi import Query
from pydantic import AfterValidator, BaseModel, EmailStr, Field, model_validator

T = TypeVar("T")


def _normalizar_email(valor: str) -> str:
    return valor.strip().lower()


def _validar_forca_senha(valor: str) -> str:
    if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("A senha deve conter ao menos uma letra e um número")
    return valor


NormalizedEmail = Annotated[EmailStr, AfterValidator(_normalizar_email)]
Senha = Annotated[
    str, Field(min_length=8, max_length=128), AfterValidator(_validar_forca_senha)
]


class ErrorResponse(BaseModel):
    detail: str


_DESCRICOES = {
    401: "Não autenticado ou token inválido/expirado",
    403: "Sem permissão para esta operação",
    404: "Recurso não encontrado",
    409: "Conflito (duplicidade ou estado inválido)",
    422: "Dados inválidos ou regra de negócio violada",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": ErrorResponse, "description": _DESCRICOES[c]} for c in codes}


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Número da página (começa em 1)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Itens por página")] = 20,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def make_page(items: Sequence[Any], total: int, p: Pagination) -> dict[str, Any]:
    return {
        "items": list(items),
        "total": total,
        "page": p.page,
        "page_size": p.page_size,
        "pages": math.ceil(total / p.page_size) if total else 0,
    }


class PartialUpdateModel(BaseModel):
    """Base para PUT/PATCH parciais: exige ao menos 1 campo e proíbe null nos não-anuláveis."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _validar_parcial(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        for campo in self.model_fields_set - self.nullable_fields:
            if getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ser nulo")
        return self
