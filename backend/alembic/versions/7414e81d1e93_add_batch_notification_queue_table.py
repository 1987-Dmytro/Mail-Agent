"""add_batch_notification_queue_table

Revision ID: 7414e81d1e93
Revises: 24f53959fa17
Create Date: 2025-11-30 17:39:55.427732

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7414e81d1e93'
down_revision: Union[str, Sequence[str], None] = '24f53959fa17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create batch_notification_queue table for Story 2.3
    op.create_table('batch_notification_queue',
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email_id', sa.Integer(), nullable=False),
    sa.Column('telegram_id', sa.String(length=50), nullable=False),
    sa.Column('message_text', sa.Text(), nullable=False),
    sa.Column('buttons_json', sa.Text(), nullable=True),
    sa.Column('priority_score', sa.Integer(), nullable=False),
    sa.Column('scheduled_for', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_batch_notification_queue_email_id'), 'batch_notification_queue', ['email_id'], unique=True)
    op.create_index(op.f('ix_batch_notification_queue_scheduled_for'), 'batch_notification_queue', ['scheduled_for'], unique=False)
    op.create_index(op.f('ix_batch_notification_queue_status'), 'batch_notification_queue', ['status'], unique=False)
    op.create_index(op.f('ix_batch_notification_queue_user_id'), 'batch_notification_queue', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop batch_notification_queue table
    op.drop_index(op.f('ix_batch_notification_queue_user_id'), table_name='batch_notification_queue')
    op.drop_index(op.f('ix_batch_notification_queue_status'), table_name='batch_notification_queue')
    op.drop_index(op.f('ix_batch_notification_queue_scheduled_for'), table_name='batch_notification_queue')
    op.drop_index(op.f('ix_batch_notification_queue_email_id'), table_name='batch_notification_queue')
    op.drop_table('batch_notification_queue')
