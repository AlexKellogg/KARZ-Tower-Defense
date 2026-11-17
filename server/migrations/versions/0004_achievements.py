"""achievements

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('achievements',
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('achievement_id', sa.String(length=40), nullable=False),
    sa.Column('unlocked_at', sa.String(length=19), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('account_id', 'achievement_id')
    )


def downgrade():
    op.drop_table('achievements')
