"""Geração de protocolos de chamados, ex.: HD-20260929-A1B2C3D4."""

import secrets
from datetime import datetime

from app.utils.tempo import utcnow


def gerar_protocolo(agora: datetime | None = None) -> str:
    agora = agora or utcnow()
    return f"HD-{agora:%Y%m%d}-{secrets.token_hex(4).upper()}"
