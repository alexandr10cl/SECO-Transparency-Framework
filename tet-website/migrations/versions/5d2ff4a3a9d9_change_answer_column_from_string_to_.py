"""Change answer column from String to Integer for 0-100 scale

Revision ID: 5d2ff4a3a9d9
Revises: c1e1d708ec8c
Create Date: 2025-08-06 22:05:38.479005

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d2ff4a3a9d9'
down_revision = 'c1e1d708ec8c'
branch_labels = None
depends_on = None


def upgrade():
    # Add new integer column
    with op.batch_alter_table('answer', schema=None) as batch_op:
        batch_op.add_column(sa.Column('answer_numeric', sa.Integer(), nullable=True))
    
    # Migrate existing data
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE answer 
        SET answer_numeric = CASE 
            WHEN LOWER(TRIM(answer)) = 'yes' THEN 100
            WHEN LOWER(TRIM(answer)) = 'partial' THEN 50 
            WHEN LOWER(TRIM(answer)) = 'no' THEN 0
            ELSE 50
        END
    """))
    
    # Drop old column and rename new one
    with op.batch_alter_table('answer', schema=None) as batch_op:
        batch_op.drop_column('answer')
        batch_op.alter_column('answer_numeric', new_column_name='answer', nullable=False)


def downgrade():
    # Add back string column
    with op.batch_alter_table('answer', schema=None) as batch_op:
        batch_op.add_column(sa.Column('answer_string', sa.String(1000), nullable=True))
    
    # Convert numeric values back to strings
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE answer 
        SET answer_string = CASE 
            WHEN answer >= 75 THEN 'yes'
            WHEN answer >= 25 THEN 'partial'
            ELSE 'no'
        END
    """))
    
    # Drop numeric column and rename string one back
    with op.batch_alter_table('answer', schema=None) as batch_op:
        batch_op.drop_column('answer')
        batch_op.alter_column('answer_string', new_column_name='answer', nullable=False)
