"""add scenario personalization tables

Revision ID: c3f8a92d1e6b
Revises: b6f8b8ba394e
Create Date: 2026-09-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3f8a92d1e6b'
down_revision = 'b6f8b8ba394e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('portal_collection',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'DONE', 'ERROR', name='status_collection_enum'), nullable=False),
    sa.Column('dados_portal', sa.JSON(), nullable=True),
    sa.Column('modo_coleta', sa.String(length=20), nullable=True),
    sa.Column('motivos_degradacao', sa.JSON(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.Column('evaluation_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluation.evaluation_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('portal_collection', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_portal_collection_evaluation_id'), ['evaluation_id'], unique=True)

    op.create_table('personalized_scenario',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'AWAITING_APPROVAL', 'APPROVED', 'ERROR', name='status_scenario_enum'), nullable=False),
    sa.Column('cenario_personalizado', sa.Text(), nullable=True),
    sa.Column('etapas_omitidas', sa.JSON(), nullable=True),
    sa.Column('recursos_confirmados', sa.JSON(), nullable=True),
    sa.Column('justificativas', sa.JSON(), nullable=True),
    sa.Column('recursos_removidos_validacao', sa.JSON(), nullable=True),
    sa.Column('cenario_base_title_snapshot', sa.String(length=100), nullable=True),
    sa.Column('cenario_base_description_snapshot', sa.Text(), nullable=True),
    sa.Column('manager_description_snapshot', sa.Text(), nullable=True),
    sa.Column('provider', sa.String(length=50), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('tokens_total', sa.Integer(), nullable=True),
    sa.Column('ai_duration_s', sa.Float(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.Column('evaluation_id', sa.BigInteger(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('portal_collection_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluation.evaluation_id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['task.task_id'], ),
    sa.ForeignKeyConstraint(['portal_collection_id'], ['portal_collection.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('evaluation_id', 'task_id', name='uq_personalized_scenario_evaluation_task')
    )
    with op.batch_alter_table('personalized_scenario', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_personalized_scenario_evaluation_id'), ['evaluation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_personalized_scenario_task_id'), ['task_id'], unique=False)

    op.create_table('scenario_approval_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.Enum('APPROVED', 'REJECTED', name='scenario_approval_decision_enum'), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('decided_at', sa.DateTime(), nullable=False),
    sa.Column('personalized_scenario_id', sa.Integer(), nullable=False),
    sa.Column('reviewer_user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['personalized_scenario_id'], ['personalized_scenario.id'], ),
    sa.ForeignKeyConstraint(['reviewer_user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('scenario_approval_log', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_scenario_approval_log_personalized_scenario_id'), ['personalized_scenario_id'], unique=False)


def downgrade():
    # Sem drop_index explicito: no MySQL um indice que sustenta uma foreign key nao pode
    # ser removido enquanto a FK existir (erro 1553), e `drop_table` ja leva junto os
    # indices da tabela. A ordem abaixo respeita as dependencias das FKs.
    op.drop_table('scenario_approval_log')
    op.drop_table('personalized_scenario')
    op.drop_table('portal_collection')
