"""add_dlq_reason_field

Revision ID: 011d456c41b6
Revises: 56e98b3cade0
Create Date: 2025-11-08 12:28:11.768483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011d456c41b6'
down_revision: Union[str, Sequence[str], None] = '56e98b3cade0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add dlq_reason field for Dead Letter Queue tracking."""
    # Add dlq_reason column
    op.add_column('email_processing_queue', sa.Column('dlq_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove dlq_reason field."""
    # Remove dlq_reason column
    op.drop_column('email_processing_queue', 'dlq_reason')
