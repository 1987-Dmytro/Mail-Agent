"""add_error_fields_to_email_processing_queue

Revision ID: 56e98b3cade0
Revises: 38bee09c03df
Create Date: 2025-11-08 12:13:56.766974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56e98b3cade0'
down_revision: Union[str, Sequence[str], None] = '38bee09c03df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add error handling fields to email_processing_queue."""
    # Add error_type column
    op.add_column('email_processing_queue', sa.Column('error_type', sa.String(length=100), nullable=True))

    # Add error_message column
    op.add_column('email_processing_queue', sa.Column('error_message', sa.Text(), nullable=True))

    # Add error_timestamp column
    op.add_column('email_processing_queue', sa.Column('error_timestamp', sa.DateTime(timezone=True), nullable=True))

    # Add retry_count column with default 0
    op.add_column('email_processing_queue', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema - Remove error handling fields from email_processing_queue."""
    # Remove columns in reverse order
    op.drop_column('email_processing_queue', 'retry_count')
    op.drop_column('email_processing_queue', 'error_timestamp')
    op.drop_column('email_processing_queue', 'error_message')
    op.drop_column('email_processing_queue', 'error_type')
