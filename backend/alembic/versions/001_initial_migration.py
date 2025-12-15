"""Initial migration with TimescaleDB setup

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

    # Create batteries table
    op.create_table(
        'batteries',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(length=50), nullable=False, comment='Battery name (e.g., \'Batt1\', \'Batt2\', \'Batt3\')'),
        sa.Column('ip_address', sa.String(length=15), nullable=False, comment='Device IP address'),
        sa.Column('udp_port', sa.Integer(), nullable=False, comment='UDP port for API communication'),
        sa.Column('ble_mac', sa.String(length=12), nullable=False, comment='Bluetooth MAC address'),
        sa.Column('wifi_mac', sa.String(length=12), nullable=False, comment='WiFi MAC address'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Whether battery is active'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True, comment='Last time battery was seen'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ble_mac')
    )
    op.create_index(op.f('ix_batteries_ble_mac'), 'batteries', ['ble_mac'], unique=True)

    # Create schedule_configs table
    op.create_table(
        'schedule_configs',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Schedule name (e.g., \'Auto Day\', \'Manual Night\')'),
        sa.Column('mode_type', sa.String(length=20), nullable=False, comment='Mode type: \'auto\', \'manual_night\', \'tempo_red\', etc.'),
        sa.Column('start_time', sa.Time(), nullable=False, comment='Start time for this schedule'),
        sa.Column('end_time', sa.Time(), nullable=False, comment='End time for this schedule'),
        sa.Column('week_days', sa.Integer(), nullable=False, server_default=sa.text('127'), comment='Week days bitmap: 0-127 (1=Monday, 3=Mon+Tue, 127=all week)'),
        sa.Column('power_setpoint', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='Power setpoint [W] (0 = no limit)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Whether schedule is active'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create battery_status_logs table (will become hypertable)
    op.create_table(
        'battery_status_logs',
        sa.Column('battery_id', sa.Integer(), nullable=False, comment='Foreign key to batteries table'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, comment='Timestamp of the status reading'),
        sa.Column('soc', sa.Integer(), nullable=False, comment='State of Charge [%]'),
        sa.Column('bat_power', sa.Float(), nullable=True, comment='Battery power [W]'),
        sa.Column('pv_power', sa.Float(), nullable=True, comment='Photovoltaic power [W]'),
        sa.Column('ongrid_power', sa.Float(), nullable=True, comment='Grid-tied power [W]'),
        sa.Column('offgrid_power', sa.Float(), nullable=True, comment='Off-grid power [W]'),
        sa.Column('mode', sa.String(length=20), nullable=False, comment='Device mode (Auto, Manual, AI, Passive)'),
        sa.Column('bat_temp', sa.Float(), nullable=True, comment='Battery temperature [°C]'),
        sa.Column('bat_capacity', sa.Float(), nullable=True, comment='Battery remaining capacity [Wh]'),
        sa.ForeignKeyConstraint(['battery_id'], ['batteries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('battery_id', 'timestamp')
    )
    op.create_index(op.f('ix_battery_status_logs_timestamp'), 'battery_status_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_battery_status_logs_battery_id'), 'battery_status_logs', ['battery_id'], unique=False)

    # Convert battery_status_logs to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable(
            'battery_status_logs',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );
    """)

    # Create APScheduler jobs table (will be created by APScheduler if not exists)
    # But we create it here to ensure it exists
    op.create_table(
        'apscheduler_jobs',
        sa.Column('id', sa.String(length=191), nullable=False),
        sa.Column('next_run_time', sa.Float(), nullable=True),
        sa.Column('job_state', sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs', ['next_run_time'], unique=False)


def downgrade() -> None:
    # Drop hypertable (TimescaleDB will handle this)
    op.execute("SELECT drop_hypertable('battery_status_logs', if_exists => TRUE);")
    
    # Drop tables
    op.drop_index(op.f('ix_battery_status_logs_battery_id'), table_name='battery_status_logs')
    op.drop_index(op.f('ix_battery_status_logs_timestamp'), table_name='battery_status_logs')
    op.drop_table('battery_status_logs')
    op.drop_table('schedule_configs')
    op.drop_index(op.f('ix_batteries_ble_mac'), table_name='batteries')
    op.drop_table('batteries')
    
    # Drop TimescaleDB extension (optional, may be used by other tables)
    # op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")

