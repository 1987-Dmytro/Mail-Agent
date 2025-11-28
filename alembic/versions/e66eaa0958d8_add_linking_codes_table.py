"""add_linking_codes_table

Revision ID: e66eaa0958d8
Revises: 93c2f08178be
Create Date: 2025-11-07 11:56:09.189795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e66eaa0958d8'
down_revision: Union[str, Sequence[str], None] = '93c2f08178be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create linking_codes table
    op.create_table(
        'linking_codes',
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    # Create index on code column for fast lookups
    op.create_index('ix_linking_codes_code', 'linking_codes', ['code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index('ix_linking_codes_code', table_name='linking_codes')
    # Drop table
    op.drop_table('linking_codes')
