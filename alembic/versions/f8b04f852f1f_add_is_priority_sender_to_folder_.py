"""add is_priority_sender to folder_categories

Revision ID: f8b04f852f1f
Revises: 5b575ce152bd
Create Date: 2025-11-08 10:44:37.033847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8b04f852f1f'
down_revision: Union[str, Sequence[str], None] = '5b575ce152bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_priority_sender column to folder_categories table
    op.add_column('folder_categories', sa.Column('is_priority_sender', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove is_priority_sender column from folder_categories table
    op.drop_column('folder_categories', 'is_priority_sender')
