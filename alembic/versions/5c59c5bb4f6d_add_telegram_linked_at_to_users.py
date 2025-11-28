"""add_telegram_linked_at_to_users

Revision ID: 5c59c5bb4f6d
Revises: e66eaa0958d8
Create Date: 2025-11-07 11:56:31.383750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c59c5bb4f6d'
down_revision: Union[str, Sequence[str], None] = 'e66eaa0958d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add telegram_linked_at column to users table
    op.add_column('users', sa.Column('telegram_linked_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop telegram_linked_at column from users table
    op.drop_column('users', 'telegram_linked_at')
