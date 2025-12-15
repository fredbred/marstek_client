"""Add performance indexes

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2024-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_indexes'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for common queries."""
    # Index for filtering active batteries
    op.create_index(
        'ix_batteries_is_active',
        'batteries',
        ['is_active'],
        unique=False,
    )
    
    # Index for filtering by IP address (for discovery)
    op.create_index(
        'ix_batteries_ip_address',
        'batteries',
        ['ip_address'],
        unique=False,
    )
    
    # Composite index for status logs queries (battery_id + timestamp)
    op.create_index(
        'ix_battery_status_logs_battery_timestamp',
        'battery_status_logs',
        ['battery_id', 'timestamp'],
        unique=False,
    )
    
    # Index for filtering schedules by active status
    op.create_index(
        'ix_schedule_configs_is_active',
        'schedule_configs',
        ['is_active'],
        unique=False,
    )
    
    # Index for filtering schedules by mode_type
    op.create_index(
        'ix_schedule_configs_mode_type',
        'schedule_configs',
        ['mode_type'],
        unique=False,
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('ix_schedule_configs_mode_type', table_name='schedule_configs')
    op.drop_index('ix_schedule_configs_is_active', table_name='schedule_configs')
    op.drop_index('ix_battery_status_logs_battery_timestamp', table_name='battery_status_logs')
    op.drop_index('ix_batteries_ip_address', table_name='batteries')
    op.drop_index('ix_batteries_is_active', table_name='batteries')
