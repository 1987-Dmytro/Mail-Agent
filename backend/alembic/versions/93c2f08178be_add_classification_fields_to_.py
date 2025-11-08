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
    # Add classification type column
    op.add_column('email_processing_queue', sa.Column('classification', sa.String(50), nullable=True))

    # Add proposed_folder_id column (MUST exist before FK constraint)
    op.add_column('email_processing_queue', sa.Column('proposed_folder_id', sa.Integer(), nullable=True))

    # Add classification_reasoning column
    op.add_column('email_processing_queue', sa.Column('classification_reasoning', sa.Text(), nullable=True))

    # Add priority_score column
    op.add_column('email_processing_queue', sa.Column('priority_score', sa.Integer(), nullable=False, server_default='0'))

    # Add is_priority column
    op.add_column('email_processing_queue', sa.Column('is_priority', sa.Boolean(), nullable=False, server_default='false'))

    # Add foreign key constraint to proposed_folder_id
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

    # Drop columns (reverse order of creation)
    op.drop_column('email_processing_queue', 'is_priority')
    op.drop_column('email_processing_queue', 'priority_score')
    op.drop_column('email_processing_queue', 'classification_reasoning')
    op.drop_column('email_processing_queue', 'proposed_folder_id')
    op.drop_column('email_processing_queue', 'classification')
