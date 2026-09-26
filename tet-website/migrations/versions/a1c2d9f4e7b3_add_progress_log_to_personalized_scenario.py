"""add progress_log to personalized_scenario

Revision ID: a1c2d9f4e7b3
Revises: c3f8a92d1e6b
Create Date: 2026-09-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c2d9f4e7b3'
down_revision = 'c3f8a92d1e6b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('personalized_scenario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('progress_log', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('model_switches', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('final_attempt', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('personalized_scenario', schema=None) as batch_op:
        batch_op.drop_column('final_attempt')
        batch_op.drop_column('model_switches')
        batch_op.drop_column('progress_log')
