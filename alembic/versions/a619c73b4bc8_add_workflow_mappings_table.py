"""add_workflow_mappings_table

Revision ID: a619c73b4bc8
Revises: 5c59c5bb4f6d
Create Date: 2025-11-07 15:51:10.506011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a619c73b4bc8'
down_revision: Union[str, Sequence[str], None] = '5c59c5bb4f6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create workflow_mappings table for LangGraph workflow tracking."""
    # Create workflow_mappings table
    op.create_table(
        'workflow_mappings',
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('telegram_message_id', sa.String(length=100), nullable=True),
        sa.Column('workflow_state', sa.String(length=50), nullable=False, server_default='initialized'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['email_id'], ['email_processing_queue.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_id'),
        sa.UniqueConstraint('thread_id')
    )

    # Create indexes for fast lookup during callback reconnection
    op.create_index('ix_workflow_mappings_email_id', 'workflow_mappings', ['email_id'], unique=True)
    op.create_index('ix_workflow_mappings_thread_id', 'workflow_mappings', ['thread_id'], unique=True)
    op.create_index('idx_workflow_mappings_thread_id', 'workflow_mappings', ['thread_id'], unique=False)
    op.create_index('idx_workflow_mappings_user_state', 'workflow_mappings', ['user_id', 'workflow_state'], unique=False)
    op.create_index('ix_workflow_mappings_user_id', 'workflow_mappings', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Drop workflow_mappings table."""
    # Drop indexes first
    op.drop_index('ix_workflow_mappings_user_id', table_name='workflow_mappings')
    op.drop_index('idx_workflow_mappings_user_state', table_name='workflow_mappings')
    op.drop_index('idx_workflow_mappings_thread_id', table_name='workflow_mappings')
    op.drop_index('ix_workflow_mappings_thread_id', table_name='workflow_mappings')
    op.drop_index('ix_workflow_mappings_email_id', table_name='workflow_mappings')
    # Drop table
    op.drop_table('workflow_mappings')
