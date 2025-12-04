"""add_version_field_for_optimistic_locking

Revision ID: a1b2c3d4e5f6
Revises: 7414e81d1e93
Create Date: 2025-12-03 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7414e81d1e93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add version field for optimistic locking to email_processing_queue."""
    # Add version column with default value 1 for existing rows
    op.add_column('email_processing_queue', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema - Remove version field from email_processing_queue."""
    op.drop_column('email_processing_queue', 'version')
