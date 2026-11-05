"""checkpoints

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('checkpoints',
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('mode', sa.String(length=10), nullable=False),
    sa.Column('state', sa.Text(), nullable=False),
    sa.Column('saved_at', sa.String(length=19), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('account_id', 'difficulty', 'mode')
    )


def downgrade():
    op.drop_table('checkpoints')
