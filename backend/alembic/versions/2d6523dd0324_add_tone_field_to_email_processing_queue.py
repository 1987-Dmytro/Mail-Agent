"""add_tone_field_to_email_processing_queue

Revision ID: 2d6523dd0324
Revises: f21dea91e261
Create Date: 2025-11-10 11:59:17.381742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d6523dd0324'
down_revision: Union[str, Sequence[str], None] = 'f21dea91e261'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tone field to email_processing_queue table."""
    op.add_column(
        'email_processing_queue',
        sa.Column('tone', sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    """Remove tone field from email_processing_queue table."""
    op.drop_column('email_processing_queue', 'tone')
