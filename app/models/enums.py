"""Enums de domínio e helper para persisti-los como VARCHAR (sem tipo ENUM nativo)."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class PerfilUsuario(StrEnum):
    administrador = "administrador"
    tecnico = "tecnico"
    cliente = "cliente"


class PrioridadeChamado(StrEnum):
    baixa = "baixa"
    media = "media"
    alta = "alta"
    critica = "critica"


class StatusChamado(StrEnum):
    aberto = "aberto"
    em_atendimento = "em_atendimento"
    aguardando_cliente = "aguardando_cliente"
    resolvido = "resolvido"
    fechado = "fechado"
    cancelado = "cancelado"


class AcaoHistorico(StrEnum):
    criacao = "criacao"
    atualizacao = "atualizacao"
    atribuicao = "atribuicao"
    mudanca_status = "mudanca_status"


def sa_enum(enum_cls: type[StrEnum], length: int) -> SAEnum:
    """VARCHAR + validação no SQLAlchemy. Evita ALTER TYPE nas migrations ao mudar valores."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
