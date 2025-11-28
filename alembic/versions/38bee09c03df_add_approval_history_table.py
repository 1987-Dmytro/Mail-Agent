"""add approval_history table

Revision ID: 38bee09c03df
Revises: f8b04f852f1f
Create Date: 2025-11-08 11:20:01.502402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38bee09c03df'
down_revision: Union[str, Sequence[str], None] = 'f8b04f852f1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create approval_history table for tracking user approval decisions."""
    # Create approval_history table
    op.create_table(
        'approval_history',
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email_queue_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('ai_suggested_folder_id', sa.Integer(), nullable=True),
        sa.Column('user_selected_folder_id', sa.Integer(), nullable=True),
        sa.Column('approved', sa.Boolean(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['email_queue_id'], ['email_processing_queue.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ai_suggested_folder_id'], ['folder_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_selected_folder_id'], ['folder_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries (AC #7)
    # Compound index for date-range queries on user history (most common query pattern)
    op.create_index('idx_approval_history_user_timestamp', 'approval_history', ['user_id', 'timestamp'], unique=False)
    # Single index on action_type for filtering by decision type
    op.create_index('idx_approval_history_action_type', 'approval_history', ['action_type'], unique=False)
    # Index on user_id for foreign key performance
    op.create_index('ix_approval_history_user_id', 'approval_history', ['user_id'], unique=False)
    # Index on timestamp for chronological queries
    op.create_index('ix_approval_history_timestamp', 'approval_history', ['timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Drop approval_history table."""
    # Drop indexes first
    op.drop_index('ix_approval_history_timestamp', table_name='approval_history')
    op.drop_index('ix_approval_history_user_id', table_name='approval_history')
    op.drop_index('idx_approval_history_action_type', table_name='approval_history')
    op.drop_index('idx_approval_history_user_timestamp', table_name='approval_history')
    # Drop table
    op.drop_table('approval_history')
