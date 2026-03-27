"""create order_items table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mirrors the MonitoringStoppedReason enum in app/models/enums.py
# create_type=False: we manage creation/deletion manually via raw SQL below
monitoring_stopped_reason = PgEnum(
    "return_window_closed", "user_disabled", "delivered_and_settled", "item_unavailable",
    name="monitoringstoppedreason",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE monitoringstoppedreason AS ENUM (
                'return_window_closed', 'user_disabled', 'delivered_and_settled', 'item_unavailable'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    op.create_table(
        "order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("variant", sa.String(255), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("paid_price", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column(
            "is_monitoring_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("monitoring_stopped_reason", monitoring_stopped_reason, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_user_id", "order_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_user_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.execute(sa.text("DROP TYPE IF EXISTS monitoringstoppedreason"))
