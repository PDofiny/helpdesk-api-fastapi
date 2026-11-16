"""esquema inicial

Revision ID: 0001
Revises: 
Create Date: 2026-09-29 21:21:43.536111
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('senha_hash', sa.String(length=255), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('perfil', sa.Enum('administrador', 'tecnico', 'cliente', name='perfilusuario', native_enum=False, length=20), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usuarios'))
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)
    op.create_index(op.f('ix_usuarios_perfil'), 'usuarios', ['perfil'], unique=False)
    op.create_table('clientes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('telefone', sa.String(length=30), nullable=True),
    sa.Column('empresa', sa.String(length=150), nullable=True),
    sa.Column('ativo', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_clientes_usuario_id_usuarios'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clientes')),
    sa.UniqueConstraint('usuario_id', name=op.f('uq_clientes_usuario_id'))
    )
    op.create_index(op.f('ix_clientes_email'), 'clientes', ['email'], unique=True)
    op.create_table('tecnicos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('especialidade', sa.String(length=100), nullable=False),
    sa.Column('ativo', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_tecnicos_usuario_id_usuarios'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tecnicos')),
    sa.UniqueConstraint('usuario_id', name=op.f('uq_tecnicos_usuario_id'))
    )
    op.create_index(op.f('ix_tecnicos_email'), 'tecnicos', ['email'], unique=True)
    op.create_table('chamados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('protocolo', sa.String(length=30), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('prioridade', sa.Enum('baixa', 'media', 'alta', 'critica', name='prioridadechamado', native_enum=False, length=20), nullable=False),
    sa.Column('status', sa.Enum('aberto', 'em_atendimento', 'aguardando_cliente', 'resolvido', 'fechado', 'cancelado', name='statuschamado', native_enum=False, length=30), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=False),
    sa.Column('tecnico_id', sa.Integer(), nullable=True),
    sa.Column('data_abertura', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('data_atualizacao', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('data_fechamento', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], name=op.f('fk_chamados_cliente_id_clientes'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tecnico_id'], ['tecnicos.id'], name=op.f('fk_chamados_tecnico_id_tecnicos'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chamados'))
    )
    op.create_index(op.f('ix_chamados_cliente_id'), 'chamados', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_chamados_prioridade'), 'chamados', ['prioridade'], unique=False)
    op.create_index(op.f('ix_chamados_protocolo'), 'chamados', ['protocolo'], unique=True)
    op.create_index(op.f('ix_chamados_status'), 'chamados', ['status'], unique=False)
    op.create_index(op.f('ix_chamados_tecnico_id'), 'chamados', ['tecnico_id'], unique=False)
    op.create_table('historico_chamados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chamado_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('acao', sa.String(length=50), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('data', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['chamado_id'], ['chamados.id'], name=op.f('fk_historico_chamados_chamado_id_chamados'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_historico_chamados_usuario_id_usuarios'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_historico_chamados'))
    )
    op.create_index(op.f('ix_historico_chamados_chamado_id'), 'historico_chamados', ['chamado_id'], unique=False)
    op.create_index(op.f('ix_historico_chamados_usuario_id'), 'historico_chamados', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_historico_chamados_usuario_id'), table_name='historico_chamados')
    op.drop_index(op.f('ix_historico_chamados_chamado_id'), table_name='historico_chamados')
    op.drop_table('historico_chamados')
    op.drop_index(op.f('ix_chamados_tecnico_id'), table_name='chamados')
    op.drop_index(op.f('ix_chamados_status'), table_name='chamados')
    op.drop_index(op.f('ix_chamados_protocolo'), table_name='chamados')
    op.drop_index(op.f('ix_chamados_prioridade'), table_name='chamados')
    op.drop_index(op.f('ix_chamados_cliente_id'), table_name='chamados')
    op.drop_table('chamados')
    op.drop_index(op.f('ix_tecnicos_email'), table_name='tecnicos')
    op.drop_table('tecnicos')
    op.drop_index(op.f('ix_clientes_email'), table_name='clientes')
    op.drop_table('clientes')
    op.drop_index(op.f('ix_usuarios_perfil'), table_name='usuarios')
    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')
