"""add ai analysis tables

Revision ID: b7d2e4a91c36
Revises: 1141a64c9458
Create Date: 2026-08-21 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d2e4a91c36'
down_revision = '1141a64c9458'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ai_analysis',
    sa.Column('ai_analysis_id', sa.Integer(), nullable=False),
    sa.Column('evaluation_id', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'DONE', 'ERROR', name='ai_analysis_status_enum'), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('provider', sa.String(length=50), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('participants_total', sa.Integer(), nullable=True),
    sa.Column('tokens_total', sa.Integer(), nullable=True),
    sa.Column('ai_duration_s', sa.Float(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.Column('debug', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluation.evaluation_id'], ),
    sa.PrimaryKeyConstraint('ai_analysis_id')
    )
    with op.batch_alter_table('ai_analysis', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_analysis_evaluation_id'), ['evaluation_id'], unique=True)

    op.create_table('ai_action',
    sa.Column('ai_action_id', sa.Integer(), nullable=False),
    sa.Column('ai_analysis_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('where_to_act', sa.JSON(), nullable=False),
    sa.Column('decision', sa.Enum('NEW', 'ACCEPTED', 'DISMISSED', name='ai_review_status_enum'), nullable=False),
    sa.ForeignKeyConstraint(['ai_analysis_id'], ['ai_analysis.ai_analysis_id'], ),
    sa.PrimaryKeyConstraint('ai_action_id')
    )
    with op.batch_alter_table('ai_action', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_action_ai_analysis_id'), ['ai_analysis_id'], unique=False)

    op.create_table('ai_finding',
    sa.Column('ai_finding_id', sa.Integer(), nullable=False),
    sa.Column('ai_analysis_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('observation', sa.Text(), nullable=False),
    sa.Column('ksc_id', sa.Integer(), nullable=False),
    sa.Column('evidence', sa.JSON(), nullable=False),
    sa.Column('review_status', sa.Enum('NEW', 'ACCEPTED', 'DISMISSED', name='ai_review_status_enum'), nullable=False),
    sa.ForeignKeyConstraint(['ai_analysis_id'], ['ai_analysis.ai_analysis_id'], ),
    sa.ForeignKeyConstraint(['ksc_id'], ['key_success_criterion.key_success_criterion_id'], ),
    sa.PrimaryKeyConstraint('ai_finding_id')
    )
    with op.batch_alter_table('ai_finding', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_finding_ai_analysis_id'), ['ai_analysis_id'], unique=False)

    op.create_table('ai_action_finding',
    sa.Column('ai_action_id', sa.Integer(), nullable=False),
    sa.Column('ai_finding_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['ai_action_id'], ['ai_action.ai_action_id'], ),
    sa.ForeignKeyConstraint(['ai_finding_id'], ['ai_finding.ai_finding_id'], ),
    sa.PrimaryKeyConstraint('ai_action_id', 'ai_finding_id')
    )


def downgrade():
    # Sem drop_index explicito: no MySQL um indice que sustenta uma foreign key nao pode
    # ser removido enquanto a FK existir (erro 1553), e `drop_table` ja leva junto os
    # indices da tabela. A ordem abaixo respeita as dependencias das FKs.
    op.drop_table('ai_action_finding')
    op.drop_table('ai_finding')
    op.drop_table('ai_action')
    op.drop_table('ai_analysis')
