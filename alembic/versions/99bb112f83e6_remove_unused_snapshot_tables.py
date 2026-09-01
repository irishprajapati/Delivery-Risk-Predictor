"""remove_unused_snapshot_tables

Revision ID: 99bb112f83e6
Revises: 887c096a1fc8
Create Date: 2026-09-01 17:23:29.381796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99bb112f83e6'
down_revision: Union[str, Sequence[str], None] = '887c096a1fc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop unused snapshot tables that are never populated or used
    op.drop_table('operational_snapshots')
    op.drop_table('environment_snapshots')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the tables if rollback is needed
    op.create_table(
        'environment_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('weather', sa.String()),
        sa.Column('rainfall', sa.Float()),
        sa.Column('temperature', sa.Float()),
        sa.Column('traffic_level', sa.String()),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'])
    )
    op.create_table(
        'operational_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('rider_load', sa.Integer(), server_default='0'),
        sa.Column('hub_delay_minutes', sa.Float(), server_default='0'),
        sa.Column('route_status', sa.String()),
        sa.Column('vehicle_status', sa.String()),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'])
    )
