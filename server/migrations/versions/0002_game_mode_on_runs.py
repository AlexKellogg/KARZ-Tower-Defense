"""game mode on runs

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mode', sa.String(length=10), server_default='regular', nullable=False))


def downgrade():
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.drop_column('mode')
