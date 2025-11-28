"""add notification preferences table

Revision ID: 5b575ce152bd
Revises: a619c73b4bc8
Create Date: 2025-11-08 09:30:48.879869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b575ce152bd'
down_revision: Union[str, Sequence[str], None] = 'a619c73b4bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create notification_preferences table for batch notification settings."""
    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('batch_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('batch_time', sa.Time(), nullable=False, server_default='18:00:00'),
        sa.Column('priority_immediate', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('quiet_hours_start', sa.Time(), nullable=True),
        sa.Column('quiet_hours_end', sa.Time(), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Create index for fast lookup by user_id
    op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema: Drop notification_preferences table."""
    # Drop index first
    op.drop_index('ix_notification_preferences_user_id', table_name='notification_preferences')
    # Drop table
    op.drop_table('notification_preferences')
