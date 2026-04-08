"""create alerts table

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, JSONB, UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mirrors enums in app/models/enums.py
# create_type=False: we manage creation/deletion manually via raw SQL below
alert_type = PgEnum(
    "price_drop", "delivery_anomaly",
    "return_window_expiring", "alternative_product",
    name="alerttype",
    create_type=False,
)
alert_status = PgEnum(
    "new", "viewed", "resolved", "dismissed", "expired",
    name="alertstatus",
    create_type=False,
)
alert_priority = PgEnum(
    "high", "medium", "low",
    name="alertpriority",
    create_type=False,
)
recommended_action = PgEnum(
    "price_match", "return_and_rebuy", "no_action",
    name="recommendedaction",
    create_type=False,
)
effort_level = PgEnum(
    "low", "medium", "high",
    name="effortlevel",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE alerttype AS ENUM (
                'price_drop', 'delivery_anomaly',
                'return_window_expiring', 'alternative_product'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE alertstatus AS ENUM ('new', 'viewed', 'resolved', 'dismissed', 'expired');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE alertpriority AS ENUM ('high', 'medium', 'low');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE recommendedaction AS ENUM ('price_match', 'return_and_rebuy', 'no_action');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE effortlevel AS ENUM ('low', 'medium', 'high');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "order_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("order_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("alert_type", alert_type, nullable=False),
        sa.Column("status", alert_status, nullable=False, server_default="new"),
        sa.Column("priority", alert_priority, nullable=False, server_default="medium"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        # Recommendation fields
        sa.Column("recommended_action", recommended_action, nullable=True),
        sa.Column("estimated_savings", sa.Float(), nullable=True),
        sa.Column("estimated_effort", effort_level, nullable=True),
        sa.Column("effort_steps_estimate", sa.Integer(), nullable=True),
        sa.Column("recommendation_rationale", sa.Text(), nullable=True),
        sa.Column("days_remaining_return", sa.Integer(), nullable=True),
        sa.Column("action_deadline", sa.Date(), nullable=True),
        sa.Column("alternative_product_url", sa.Text(), nullable=True),
        sa.Column("alternative_product_price", sa.Float(), nullable=True),
        # JSONB blobs
        sa.Column("evidence", JSONB, nullable=True),
        sa.Column("generated_messages", JSONB, nullable=True),
        # Timestamps
        sa.Column("push_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_order_item_id", "alerts", ["order_item_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_order_item_id", table_name="alerts")
    op.drop_index("ix_alerts_user_id", table_name="alerts")
    op.drop_table("alerts")
    op.execute(sa.text("DROP TYPE IF EXISTS effortlevel"))
    op.execute(sa.text("DROP TYPE IF EXISTS recommendedaction"))
    op.execute(sa.text("DROP TYPE IF EXISTS alertpriority"))
    op.execute(sa.text("DROP TYPE IF EXISTS alertstatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS alerttype"))
