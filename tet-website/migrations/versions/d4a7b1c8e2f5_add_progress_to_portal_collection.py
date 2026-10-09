"""add progress to portal_collection

Revision ID: d4a7b1c8e2f5
Revises: a1c2d9f4e7b3
Create Date: 2026-10-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4a7b1c8e2f5'
down_revision = 'a1c2d9f4e7b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('portal_collection', schema=None) as batch_op:
        batch_op.add_column(sa.Column('progress', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('portal_collection', schema=None) as batch_op:
        batch_op.drop_column('progress')
