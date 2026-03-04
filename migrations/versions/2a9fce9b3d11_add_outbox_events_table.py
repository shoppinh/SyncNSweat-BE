"""Add outbox events table

Revision ID: 2a9fce9b3d11
Revises: cbd65d53c832
Create Date: 2026-03-04 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2a9fce9b3d11'
down_revision: Union[str, None] = 'cbd65d53c832'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'outbox_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('routing_key', sa.String(), nullable=False),
        sa.Column('exchange_name', sa.String(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_outbox_events_id'), 'outbox_events', ['id'], unique=False)
    op.create_index(op.f('ix_outbox_events_event_id'), 'outbox_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_outbox_events_routing_key'), 'outbox_events', ['routing_key'], unique=False)
    op.create_index(op.f('ix_outbox_events_status'), 'outbox_events', ['status'], unique=False)
    op.create_index(op.f('ix_outbox_events_next_retry_at'), 'outbox_events', ['next_retry_at'], unique=False)
    op.create_index(op.f('ix_outbox_events_published_at'), 'outbox_events', ['published_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_outbox_events_published_at'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_next_retry_at'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_status'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_routing_key'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_event_id'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_id'), table_name='outbox_events')
    op.drop_table('outbox_events')
