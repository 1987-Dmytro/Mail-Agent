"""add_dead_letter_queue_table

Revision ID: a6a9b36a7f85
Revises: cddebd81be25
Create Date: 2025-11-30 15:39:19.543407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a6a9b36a7f85'
down_revision: Union[str, Sequence[str], None] = 'cddebd81be25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Epic 1 Story 1.3: Add dead_letter_queue table."""
    # Create dead_letter_queue table for failed Gmail operations after retry exhaustion
    op.create_table('dead_letter_queue',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('email_queue_id', sa.Integer(), nullable=False),
    sa.Column('operation_type', sa.String(length=50), nullable=False),
    sa.Column('gmail_message_id', sa.String(length=255), nullable=False),
    sa.Column('label_id', sa.String(length=100), nullable=True),
    sa.Column('error_type', sa.String(length=100), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=False),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('last_retry_at', sa.DateTime(), nullable=False),
    sa.Column('context_json', sa.Text(), nullable=True),
    sa.Column('resolved', sa.Integer(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('resolution_notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['email_queue_id'], ['email_processing_queue.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dead_letter_queue_email_queue_id'), 'dead_letter_queue', ['email_queue_id'], unique=False)
    op.create_index(op.f('ix_dead_letter_queue_gmail_message_id'), 'dead_letter_queue', ['gmail_message_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Epic 1 Story 1.3: Remove dead_letter_queue table."""
    # Drop dead_letter_queue table and its indexes
    op.drop_index(op.f('ix_dead_letter_queue_gmail_message_id'), table_name='dead_letter_queue')
    op.drop_index(op.f('ix_dead_letter_queue_email_queue_id'), table_name='dead_letter_queue')
    op.drop_table('dead_letter_queue')
