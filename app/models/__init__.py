"""Importar todos os models aqui garante que o Base.metadata conheça todas as tabelas
(necessário para o Alembic autogenerate e para os testes)."""

from app.models.chamado import Chamado
from app.models.cliente import Cliente
from app.models.enums import AcaoHistorico, PerfilUsuario, PrioridadeChamado, StatusChamado
from app.models.historico import HistoricoChamado
from app.models.tecnico import Tecnico
from app.models.usuario import Usuario

__all__ = [
    "AcaoHistorico",
    "Chamado",
    "Cliente",
    "HistoricoChamado",
    "PerfilUsuario",
    "PrioridadeChamado",
    "StatusChamado",
    "Tecnico",
    "Usuario",
]
