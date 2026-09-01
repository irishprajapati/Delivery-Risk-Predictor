from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24f6bd4d34be'
down_revision: Union[str, Sequence[str], None] = '8d2dc8100c41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""

    # ============================================================
    # 1. CREATE NEW TABLES
    # ============================================================

    op.create_table(
        'riders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('area', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('max_orders_per_day', sa.Integer(), nullable=True),
        sa.Column('current_order_count', sa.Integer(), nullable=True),
        sa.Column('completed_orders', sa.Integer(), nullable=True),
        sa.Column('failed_deliveries', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )

    op.create_index(
        op.f('ix_riders_id'),
        'riders',
        ['id'],
        unique=False
    )

    op.create_table(
        'deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('rider_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=True),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('estimated_duration', sa.Float(), nullable=True),
        sa.Column('actual_duration', sa.Float(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['rider_id'], ['riders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id')
    )

    op.create_index(
        op.f('ix_deliveries_id'),
        'deliveries',
        ['id'],
        unique=False
    )

    op.create_table(
        'delivery_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('address_quality', sa.Float(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('estimated_duration', sa.Float(), nullable=True),
        sa.Column('location_success_rate', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id')
    )

    op.create_index(
        op.f('ix_delivery_locations_id'),
        'delivery_locations',
        ['id'],
        unique=False
    )

    op.create_table(
        'environment_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('weather', sa.String(), nullable=True),
        sa.Column('rainfall', sa.Float(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('traffic_level', sa.String(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_environment_snapshots_id'),
        'environment_snapshots',
        ['id'],
        unique=False
    )

    op.create_table(
        'operational_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('rider_load', sa.Integer(), nullable=True),
        sa.Column('hub_delay_minutes', sa.Float(), nullable=True),
        sa.Column('route_status', sa.String(), nullable=True),
        sa.Column('vehicle_status', sa.String(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_operational_snapshots_id'),
        'operational_snapshots',
        ['id'],
        unique=False
    )

    # ============================================================
    # 2. REMOVE OLD TABLES
    # ============================================================

    op.drop_table('customer_profiles')
    op.drop_table('order_categories')

    # ============================================================
    # 3. ADD NEW CUSTOMER COLUMNS
    # ============================================================

    # IMPORTANT:
    # Add these as nullable first.
    # Existing customers already exist in the database.

    op.add_column(
        'customers',
        sa.Column(
            'successful_deliveries',
            sa.Integer(),
            nullable=True
        )
    )

    op.add_column(
        'customers',
        sa.Column(
            'cancellation_count',
            sa.Integer(),
            nullable=True
        )
    )

    op.add_column(
        'customers',
        sa.Column(
            'last_successful_delivery',
            sa.DateTime(),
            nullable=True
        )
    )

    # ============================================================
    # 4. INITIALIZE EXISTING CUSTOMER DATA
    # ============================================================

    op.execute("""
        UPDATE customers
        SET successful_deliveries = 0
        WHERE successful_deliveries IS NULL
    """)

    op.execute("""
        UPDATE customers
        SET cancellation_count = 0
        WHERE cancellation_count IS NULL
    """)

    op.execute("""
        UPDATE customers
        SET total_orders = 0
        WHERE total_orders IS NULL
    """)

    op.execute("""
        UPDATE customers
        SET failed_deliveries = 0
        WHERE failed_deliveries IS NULL
    """)

    op.execute("""
        UPDATE customers
        SET unreachable_count = 0
        WHERE unreachable_count IS NULL
    """)

    op.execute("""
        UPDATE customers
        SET is_verified = FALSE
        WHERE is_verified IS NULL
    """)

    # ============================================================
    # 5. NOW MAKE CUSTOMER COLUMNS NOT NULL
    # ============================================================

    op.alter_column(
        'customers',
        'successful_deliveries',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'customers',
        'cancellation_count',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'customers',
        'is_verified',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )

    op.alter_column(
        'customers',
        'total_orders',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'customers',
        'failed_deliveries',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'customers',
        'unreachable_count',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    # ============================================================
    # 6. FIX EXISTING ITEMS
    # ============================================================

    # Existing database:
    #
    # laptop   -> NULL
    # football -> NULL
    #
    # Your categories table contains:
    # 2  = computers
    # 13 = sports_equipment
    #
    # Therefore assign appropriate categories.

    op.execute("""
        UPDATE items
        SET category_id = 2
        WHERE id = 1
          AND category_id IS NULL
    """)

    op.execute("""
        UPDATE items
        SET category_id = 13
        WHERE id = 2
          AND category_id IS NULL
    """)

    # ============================================================
    # 7. MAKE ITEM COLUMNS NOT NULL
    # ============================================================

    op.alter_column(
        'items',
        'name',
        existing_type=sa.VARCHAR(),
        nullable=False
    )

    op.alter_column(
        'items',
        'price',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False
    )

    op.alter_column(
        'items',
        'category_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.create_index(
        op.f('ix_items_id'),
        'items',
        ['id'],
        unique=False
    )

    # ============================================================
    # 8. ADD NEW ORDER COLUMNS
    # ============================================================

    op.add_column(
        'orders',
        sa.Column(
            'prepaid_amount',
            sa.Float(),
            nullable=False,
            server_default='0'
        )
    )

    op.add_column(
        'orders',
        sa.Column(
            'latitude',
            sa.Float(),
            nullable=True
        )
    )

    op.add_column(
        'orders',
        sa.Column(
            'longitude',
            sa.Float(),
            nullable=True
        )
    )

    op.add_column(
        'orders',
        sa.Column(
            'risk_level',
            sa.String(),
            nullable=True
        )
    )

    # ============================================================
    # 9. FIX EXISTING ORDER DATA
    # ============================================================

    # Existing orders have NULL is_cod.
    # We are treating those existing records as non-COD.

    op.execute("""
        UPDATE orders
        SET is_cod = FALSE
        WHERE is_cod IS NULL
    """)

    # Existing orders have NULL address.
    # We need a non-null value because the new model requires it.
    #
    # This is a migration fallback for old records.

    op.execute("""
        UPDATE orders
        SET address = 'Unknown'
        WHERE address IS NULL
    """)

    # ============================================================
    # 10. MAKE ORDER COLUMNS NOT NULL
    # ============================================================

    op.alter_column(
        'orders',
        'customer_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'orders',
        'item_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'orders',
        'quantity',
        existing_type=sa.INTEGER(),
        nullable=False
    )

    op.alter_column(
        'orders',
        'total_price',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False
    )

    op.alter_column(
        'orders',
        'is_cod',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )

    op.alter_column(
        'orders',
        'address',
        existing_type=sa.VARCHAR(),
        nullable=False
    )

    op.create_index(
        op.f('ix_orders_id'),
        'orders',
        ['id'],
        unique=False
    )

    # ============================================================
    # 11. OTP
    # ============================================================

    op.alter_column(
        'otp_codes',
        'phone',
        existing_type=sa.VARCHAR(),
        nullable=False
    )

    # ============================================================
    # 12. PREDICTIONS
    # ============================================================

    op.add_column(
        'predictions',
        sa.Column(
            'order_id',
            sa.Integer(),
            nullable=True
        )
    )

    # IMPORTANT:
    # We cannot safely make order_id NOT NULL unless we know
    # how existing predictions should be linked to orders.
    #
    # Therefore we add it nullable first.

    op.drop_constraint(
        op.f('predictions_user_id_fkey'),
        'predictions',
        type_='foreignkey'
    )

    op.create_foreign_key(
        None,
        'predictions',
        'orders',
        ['order_id'],
        ['id']
    )

    # We do NOT drop user_id until we have dealt with existing
    # prediction records.
    #
    # Your current migration would delete user_id immediately,
    # which can destroy the relationship for existing records.

    op.drop_column(
        'predictions',
        'user_id'
    )

    # ============================================================
    # 13. USERS
    # ============================================================

    op.alter_column(
        'users',
        'username',
        existing_type=sa.VARCHAR(),
        nullable=False
    )

    op.alter_column(
        'users',
        'password',
        existing_type=sa.VARCHAR(),
        nullable=False
    )
def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'password',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('users', 'username',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.add_column('predictions', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'predictions', type_='foreignkey')
    op.create_foreign_key(op.f('predictions_user_id_fkey'), 'predictions', 'users', ['user_id'], ['id'])
    op.drop_column('predictions', 'order_id')
    op.alter_column('otp_codes', 'phone',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.alter_column('orders', 'address',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('orders', 'is_cod',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('orders', 'total_price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('orders', 'quantity',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('orders', 'item_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('orders', 'customer_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_column('orders', 'risk_level')
    op.drop_column('orders', 'longitude')
    op.drop_column('orders', 'latitude')
    op.drop_column('orders', 'prepaid_amount')
    op.drop_index(op.f('ix_items_id'), table_name='items')
    op.alter_column('items', 'category_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('items', 'price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('items', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('customers', 'unreachable_count',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('customers', 'failed_deliveries',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('customers', 'total_orders',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('customers', 'is_verified',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.drop_column('customers', 'last_successful_delivery')
    op.drop_column('customers', 'cancellation_count')
    op.drop_column('customers', 'successful_deliveries')
    op.create_table('order_categories',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('order_categories_pkey')),
    sa.UniqueConstraint('name', name=op.f('order_categories_name_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_table('customer_profiles',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('phone_number', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('total_orders', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('failed_deliveries', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('failure_rate', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('customer_profiles_pkey')),
    sa.UniqueConstraint('phone_number', name=op.f('customer_profiles_phone_number_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.drop_index(op.f('ix_operational_snapshots_id'), table_name='operational_snapshots')
    op.drop_table('operational_snapshots')
    op.drop_index(op.f('ix_environment_snapshots_id'), table_name='environment_snapshots')
    op.drop_table('environment_snapshots')
    op.drop_index(op.f('ix_delivery_locations_id'), table_name='delivery_locations')
    op.drop_table('delivery_locations')
    op.drop_index(op.f('ix_deliveries_id'), table_name='deliveries')
    op.drop_table('deliveries')
    op.drop_index(op.f('ix_riders_id'), table_name='riders')
    op.drop_table('riders')
    # ### end Alembic commands ###