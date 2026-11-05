"""initial schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=20), nullable=False),
    sa.Column('username_key', sa.String(length=20), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('salt', sa.LargeBinary(), nullable=False),
    sa.Column('password_hash', sa.LargeBinary(), nullable=False),
    sa.Column('role', sa.String(length=10), nullable=False),
    sa.Column('created_at', sa.String(length=19), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username_key')
    )
    op.create_table('runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('won', sa.Boolean(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('time_seconds', sa.Float(), nullable=False),
    sa.Column('lives_lost', sa.Integer(), nullable=False),
    sa.Column('waves_cleared', sa.Integer(), nullable=False),
    sa.Column('kills', sa.Integer(), nullable=False),
    sa.Column('played_at', sa.String(length=19), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_runs_account_id'), ['account_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_runs_difficulty'), ['difficulty'], unique=False)

    op.create_table('tokens',
    sa.Column('token_key', sa.String(length=64), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.String(length=19), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('token_key')
    )
    with op.batch_alter_table('tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tokens_account_id'), ['account_id'], unique=False)



def downgrade():
    with op.batch_alter_table('tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tokens_account_id'))

    op.drop_table('tokens')
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_runs_difficulty'))
        batch_op.drop_index(batch_op.f('ix_runs_account_id'))

    op.drop_table('runs')
    op.drop_table('accounts')
