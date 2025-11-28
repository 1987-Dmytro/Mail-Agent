"""add_indexing_progress_table

Revision ID: 395af0dd3ac6
Revises: 011d456c41b6
Create Date: 2025-11-09 14:39:28.016098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '395af0dd3ac6'
down_revision: Union[str, Sequence[str], None] = '011d456c41b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create indexing_progress table
    op.create_table(
        'indexing_progress',
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total_emails', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('processed_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(), nullable=False, server_default=sa.text("'in_progress'")),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_processed_message_id', sa.String(length=255), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_indexing_progress_user_id')
    )
    # Create index on user_id for fast lookups
    op.create_index('ix_indexing_progress_user_id', 'indexing_progress', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index('ix_indexing_progress_user_id', table_name='indexing_progress')
    # Drop table
    op.drop_table('indexing_progress')
