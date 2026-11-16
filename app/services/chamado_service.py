"""Regras de negócio dos chamados: visibilidade, transições de status, histórico."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.chamado import Chamado
from app.models.cliente import Cliente
from app.models.enums import AcaoHistorico, PrioridadeChamado, StatusChamado
from app.models.historico import HistoricoChamado
from app.models.tecnico import Tecnico
from app.schemas.chamado import ChamadoCreate, ChamadoStatusUpdate, ChamadoUpdate
from app.schemas.common import Pagination
from app.services.actor import Actor
from app.services.pagination import paginate
from app.utils.protocolo import gerar_protocolo
from app.utils.tempo import utcnow

S = StatusChamado

# Máquina de estados: status atual -> status permitidos a seguir.
TRANSICOES: dict[S, frozenset[S]] = {
    S.aberto: frozenset({S.em_atendimento, S.cancelado}),
    S.em_atendimento: frozenset({S.aguardando_cliente, S.resolvido, S.cancelado}),
    S.aguardando_cliente: frozenset({S.em_atendimento, S.cancelado}),
    S.resolvido: frozenset({S.fechado, S.em_atendimento}),  # em_atendimento = reabertura
    S.fechado: frozenset(),
    S.cancelado: frozenset(),
}
STATUS_FINAIS = frozenset({S.fechado, S.cancelado})
_CAMPOS_EDITAVEIS_CLIENTE = frozenset({"titulo", "descricao"})
_MAX_TENTATIVAS_PROTOCOLO = 5


# ------------------------------------------------------------------ helpers
async def _obter(db: AsyncSession, chamado_id: int, *, para_update: bool = False) -> Chamado:
    stmt = select(Chamado).where(Chamado.id == chamado_id)
    if para_update:
        stmt = stmt.with_for_update()  # evita corrida entre duas mudanças de status
    chamado = await db.scalar(stmt)
    if chamado is None:
        raise NotFoundError("Chamado não encontrado")
    return chamado


def _garantir_visibilidade(actor: Actor, chamado: Chamado) -> None:
    """Cliente só enxerga os próprios chamados; 404 (e não 403) para não vazar existência."""
    if actor.is_cliente and chamado.cliente_id != actor.cliente_id:
        raise NotFoundError("Chamado não encontrado")


def _garantir_responsavel(actor: Actor, chamado: Chamado) -> None:
    if actor.is_tecnico and chamado.tecnico_id not in (None, actor.tecnico_id):
        raise PermissionDeniedError("Este chamado está atribuído a outro técnico")


def _checar_atribuicao(actor: Actor, tecnico_id: int | None) -> None:
    if actor.is_tecnico and tecnico_id not in (None, actor.tecnico_id):
        raise PermissionDeniedError("Técnicos só podem atribuir chamados a si mesmos")


async def _validar_cliente(db: AsyncSession, cliente_id: int) -> None:
    cliente = await db.get(Cliente, cliente_id)
    if cliente is None:
        raise NotFoundError("Cliente não encontrado")
    if not cliente.ativo:
        raise BusinessRuleError("Cliente inativo")


async def _validar_tecnico(db: AsyncSession, tecnico_id: int) -> None:
    tecnico = await db.get(Tecnico, tecnico_id)
    if tecnico is None:
        raise NotFoundError("Técnico não encontrado")
    if not tecnico.ativo:
        raise BusinessRuleError("Técnico inativo")


async def _protocolo_unico(db: AsyncSession) -> str:
    for _ in range(_MAX_TENTATIVAS_PROTOCOLO):
        protocolo = gerar_protocolo()
        if await db.scalar(select(Chamado.id).where(Chamado.protocolo == protocolo)) is None:
            return protocolo
    raise ConflictError("Não foi possível gerar um protocolo único, tente novamente")


def _registrar(
    db: AsyncSession, chamado: Chamado, actor: Actor, acao: AcaoHistorico, descricao: str
) -> None:
    db.add(
        HistoricoChamado(
            chamado_id=chamado.id, usuario_id=actor.usuario.id, acao=acao.value, descricao=descricao
        )
    )


# ------------------------------------------------------------------ consultas
async def listar(
    db: AsyncSession,
    actor: Actor,
    pagination: Pagination,
    *,
    status: StatusChamado | None = None,
    prioridade: PrioridadeChamado | None = None,
    tecnico_id: int | None = None,
    cliente_id: int | None = None,
) -> tuple[list[Chamado], int]:
    stmt = select(Chamado)
    if actor.is_cliente:
        stmt = stmt.where(Chamado.cliente_id == actor.cliente_id)
    if status is not None:
        stmt = stmt.where(Chamado.status == status)
    if prioridade is not None:
        stmt = stmt.where(Chamado.prioridade == prioridade)
    if tecnico_id is not None:
        stmt = stmt.where(Chamado.tecnico_id == tecnico_id)
    if cliente_id is not None:
        stmt = stmt.where(Chamado.cliente_id == cliente_id)
    stmt = stmt.order_by(Chamado.data_abertura.desc(), Chamado.id.desc())
    return await paginate(db, stmt, pagination)


async def obter(db: AsyncSession, actor: Actor, chamado_id: int) -> Chamado:
    chamado = await _obter(db, chamado_id)
    _garantir_visibilidade(actor, chamado)
    return chamado


async def listar_historico(
    db: AsyncSession, actor: Actor, chamado_id: int, pagination: Pagination
) -> tuple[list[HistoricoChamado], int]:
    await obter(db, actor, chamado_id)  # valida existência e visibilidade
    stmt = (
        select(HistoricoChamado)
        .where(HistoricoChamado.chamado_id == chamado_id)
        .order_by(HistoricoChamado.data, HistoricoChamado.id)
    )
    return await paginate(db, stmt, pagination)


# ------------------------------------------------------------------ comandos
async def criar(db: AsyncSession, actor: Actor, data: ChamadoCreate) -> Chamado:
    tecnico_id: int | None
    if actor.is_cliente:
        if actor.cliente_id is None:
            raise BusinessRuleError("Seu usuário não possui cadastro de cliente ativo")
        if data.cliente_id not in (None, actor.cliente_id) or data.tecnico_id is not None:
            raise PermissionDeniedError(
                "Clientes só abrem chamados em nome próprio e não definem técnico"
            )
        cliente_id, tecnico_id = actor.cliente_id, None
    else:
        if data.cliente_id is None:
            raise BusinessRuleError("cliente_id é obrigatório para administradores e técnicos")
        _checar_atribuicao(actor, data.tecnico_id)
        cliente_id, tecnico_id = data.cliente_id, data.tecnico_id

    await _validar_cliente(db, cliente_id)
    if tecnico_id is not None:
        await _validar_tecnico(db, tecnico_id)

    chamado = Chamado(
        protocolo=await _protocolo_unico(db),
        titulo=data.titulo,
        descricao=data.descricao,
        prioridade=data.prioridade,
        status=StatusChamado.aberto,
        cliente_id=cliente_id,
        tecnico_id=tecnico_id,
    )
    db.add(chamado)
    await db.flush()
    _registrar(
        db, chamado, actor, AcaoHistorico.criacao, f"Chamado {chamado.protocolo} aberto"
    )
    await db.commit()
    await db.refresh(chamado)
    return chamado


async def atualizar(
    db: AsyncSession, actor: Actor, chamado_id: int, data: ChamadoUpdate
) -> Chamado:
    chamado = await _obter(db, chamado_id, para_update=True)
    _garantir_visibilidade(actor, chamado)
    if chamado.status in STATUS_FINAIS:
        raise ConflictError("Chamados fechados ou cancelados não podem ser alterados")

    campos: dict[str, Any] = data.model_dump(exclude_unset=True)

    if actor.is_cliente:
        if not set(campos) <= _CAMPOS_EDITAVEIS_CLIENTE:
            raise PermissionDeniedError("Clientes só podem alterar título e descrição")
        if chamado.status not in (S.aberto, S.aguardando_cliente):
            raise ConflictError("O chamado não pode mais ser editado pelo cliente neste status")
    elif actor.is_tecnico:
        _garantir_responsavel(actor, chamado)
        if "cliente_id" in campos:
            raise PermissionDeniedError("Apenas administradores podem trocar o cliente")
        if "tecnico_id" in campos:
            _checar_atribuicao(actor, campos["tecnico_id"])

    gerais: list[str] = []
    atribuicao: list[str] = []
    for campo, novo in campos.items():
        antigo = getattr(chamado, campo)
        if antigo == novo:
            continue
        if campo == "cliente_id":
            await _validar_cliente(db, novo)
        elif campo == "tecnico_id" and novo is not None:
            await _validar_tecnico(db, novo)
        setattr(chamado, campo, novo)
        if campo == "tecnico_id":
            atribuicao.append(f"tecnico_id: {antigo} → {novo}")
        elif campo == "descricao":
            gerais.append("descricao alterada")
        else:
            gerais.append(f"{campo}: {antigo} → {novo}")

    if not gerais and not atribuicao:
        await db.commit()  # nada mudou: apenas libera o lock
        return chamado

    chamado.data_atualizacao = utcnow()
    if gerais:
        _registrar(db, chamado, actor, AcaoHistorico.atualizacao, "; ".join(gerais))
    if atribuicao:
        _registrar(db, chamado, actor, AcaoHistorico.atribuicao, "; ".join(atribuicao))
    await db.commit()
    await db.refresh(chamado)
    return chamado


async def alterar_status(
    db: AsyncSession, actor: Actor, chamado_id: int, data: ChamadoStatusUpdate
) -> Chamado:
    chamado = await _obter(db, chamado_id, para_update=True)
    _garantir_visibilidade(actor, chamado)

    atual, novo = chamado.status, data.status
    if atual == novo:
        raise ConflictError(f"O chamado já está com status '{novo.value}'")
    if novo not in TRANSICOES[atual]:
        raise ConflictError(f"Transição de status inválida: '{atual.value}' → '{novo.value}'")

    atribuiu_a_si = False
    if actor.is_cliente:
        permitido = novo in (S.cancelado, S.fechado) or (
            novo == S.em_atendimento and atual in (S.aguardando_cliente, S.resolvido)
        )
        if not permitido:
            raise PermissionDeniedError(
                "Clientes podem cancelar, encerrar chamados resolvidos ou retomar o atendimento"
            )
    elif actor.is_tecnico:
        _garantir_responsavel(actor, chamado)
        if chamado.tecnico_id is None:
            if novo not in (S.em_atendimento, S.cancelado):
                raise BusinessRuleError("Assuma o chamado (em_atendimento) antes de alterá-lo")
            if novo == S.em_atendimento:
                if actor.tecnico_id is None:
                    raise BusinessRuleError("Seu usuário não possui cadastro de técnico ativo")
                chamado.tecnico_id = actor.tecnico_id
                atribuiu_a_si = True

    if novo == S.em_atendimento and chamado.tecnico_id is None:
        raise BusinessRuleError("Atribua um técnico antes de iniciar o atendimento")

    agora = utcnow()
    chamado.status = novo
    chamado.data_atualizacao = agora
    chamado.data_fechamento = agora if novo in STATUS_FINAIS else None

    if atribuiu_a_si:
        _registrar(
            db, chamado, actor, AcaoHistorico.atribuicao, f"tecnico_id: None → {chamado.tecnico_id}"
        )
    descricao = f"Status alterado de '{atual.value}' para '{novo.value}'"
    if data.comentario:
        descricao += f". Comentário: {data.comentario}"
    _registrar(db, chamado, actor, AcaoHistorico.mudanca_status, descricao)
    await db.commit()
    await db.refresh(chamado)
    return chamado


async def excluir(db: AsyncSession, chamado_id: int) -> None:
    """Exclusão física (somente admin). O histórico some junto via ON DELETE CASCADE."""
    await _obter(db, chamado_id)
    await db.execute(delete(Chamado).where(Chamado.id == chamado_id))
    await db.commit()
