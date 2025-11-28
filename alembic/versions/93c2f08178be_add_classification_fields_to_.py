"""Add classification fields to EmailProcessingQueue

Revision ID: 93c2f08178be
Revises: 51baa70aeef2
Create Date: 2025-11-07 09:33:02.290039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93c2f08178be'
down_revision: Union[str, Sequence[str], None] = '51baa70aeef2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add classification fields to EmailProcessingQueue."""
    # NOTE: classification, proposed_folder_id, and priority_score already exist from febde6303216 migration
    # Only add NEW columns that don't exist yet

    # Add classification_reasoning column (NEW)
    op.add_column('email_processing_queue', sa.Column('classification_reasoning', sa.Text(), nullable=True))

    # Add is_priority column (NEW)
    op.add_column('email_processing_queue', sa.Column('is_priority', sa.Boolean(), nullable=False, server_default='false'))

    # Add foreign key constraint to proposed_folder_id (which already exists)
    op.create_foreign_key(
        'fk_email_processing_queue_proposed_folder_id',
        'email_processing_queue',
        'folder_categories',
        ['proposed_folder_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema - Remove classification fields from EmailProcessingQueue."""
    # Drop foreign key constraint first
    op.drop_constraint('fk_email_processing_queue_proposed_folder_id', 'email_processing_queue', type_='foreignkey')

    # Drop only the columns that THIS migration added
    op.drop_column('email_processing_queue', 'is_priority')
    op.drop_column('email_processing_queue', 'classification_reasoning')
