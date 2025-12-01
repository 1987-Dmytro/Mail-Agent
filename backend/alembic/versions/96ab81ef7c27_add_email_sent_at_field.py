"""add_email_sent_at_field

Revision ID: 96ab81ef7c27
Revises: a6a9b36a7f85
Create Date: 2025-11-30 15:50:40.745729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '96ab81ef7c27'
down_revision: Union[str, Sequence[str], None] = 'a6a9b36a7f85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Story 2.1: Add email_sent_at field for idempotency."""
    # Add email_sent_at column to email_processing_queue table
    op.add_column('email_processing_queue',
        sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema - Story 2.1: Remove email_sent_at field."""
    # Remove email_sent_at column from email_processing_queue table
    op.drop_column('email_processing_queue', 'email_sent_at')
