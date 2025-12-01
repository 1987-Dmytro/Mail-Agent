"""add_manual_notifications_table

Revision ID: cddebd81be25
Revises: 2d6523dd0324
Create Date: 2025-11-30 15:16:44.684693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cddebd81be25'
down_revision: Union[str, Sequence[str], None] = '2d6523dd0324'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Epic 1 Story 1.1: Add manual_notifications table."""
    # Create manual_notifications table for Telegram notification fallback queue
    op.create_table('manual_notifications',
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email_id', sa.Integer(), nullable=False),
    sa.Column('telegram_id', sa.String(length=50), nullable=False),
    sa.Column('message_text', sa.Text(), nullable=False),
    sa.Column('buttons_json', sa.Text(), nullable=True),
    sa.Column('error_type', sa.String(length=100), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=False),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_manual_notifications_email_id'), 'manual_notifications', ['email_id'], unique=False)
    op.create_index(op.f('ix_manual_notifications_status'), 'manual_notifications', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Epic 1 Story 1.1: Remove manual_notifications table."""
    # Drop manual_notifications table and its indexes
    op.drop_index(op.f('ix_manual_notifications_status'), table_name='manual_notifications')
    op.drop_index(op.f('ix_manual_notifications_email_id'), table_name='manual_notifications')
    op.drop_table('manual_notifications')
