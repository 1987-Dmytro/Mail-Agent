"""add_prompt_versions_table

Revision ID: f21dea91e261
Revises: c6c872982e1e
Create Date: 2025-11-10 09:13:22.975510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f21dea91e261'
down_revision: Union[str, Sequence[str], None] = 'c6c872982e1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create prompt_versions table for storing versioned prompt templates.

    This table enables:
    - A/B testing of different prompt variations
    - Rollback to previous prompt versions
    - Tracking which prompt version generated each response
    - Refinement based on user feedback

    Story 3.6: Response Generation Prompt Engineering
    """
    # Create prompt_versions table
    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(), nullable=False),
        sa.Column('template_content', sa.Text(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    # Create index on template_name for fast lookups
    op.create_index('ix_prompt_versions_template_name', 'prompt_versions', ['template_name'], unique=False)


def downgrade() -> None:
    """Remove prompt_versions table."""
    # Drop index first
    op.drop_index('ix_prompt_versions_template_name', table_name='prompt_versions')
    # Drop table
    op.drop_table('prompt_versions')
