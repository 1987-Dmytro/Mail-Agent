"""add_detected_language_field

Revision ID: c6c872982e1e
Revises: 395af0dd3ac6
Create Date: 2025-11-09 20:15:19.040119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6c872982e1e'
down_revision: Union[str, Sequence[str], None] = '395af0dd3ac6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add detected_language field to email_processing_queue table.

    This field stores the detected language code (ru, uk, en, de) for each email,
    used by the language detection service (Story 3.5) to enable appropriate
    response generation in the correct language.
    """
    op.add_column(
        'email_processing_queue',
        sa.Column('detected_language', sa.String(length=5), nullable=True)
    )


def downgrade() -> None:
    """Remove detected_language field from email_processing_queue table."""
    op.drop_column('email_processing_queue', 'detected_language')
