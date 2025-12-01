"""add_retry_columns_to_indexing_progress

Revision ID: 24f53959fa17
Revises: 96ab81ef7c27
Create Date: 2025-11-30 16:04:31.213143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24f53959fa17'
down_revision: Union[str, Sequence[str], None] = '96ab81ef7c27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add retry_count column with default value 0
    op.add_column('indexing_progress', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    # Add retry_after column (nullable, no default)
    op.add_column('indexing_progress', sa.Column('retry_after', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove retry_after column
    op.drop_column('indexing_progress', 'retry_after')
    # Remove retry_count column
    op.drop_column('indexing_progress', 'retry_count')
