"""create price_snapshots table

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mirrors the SnapshotSource enum in app/models/enums.py
# create_type=False: we manage creation/deletion manually via raw SQL below
snapshot_source = PgEnum(
    "scheduled_job", "manual_refresh", "extension_capture",
    name="snapshotsource",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE snapshotsource AS ENUM (
                'scheduled_job', 'manual_refresh', 'extension_capture'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    op.create_table(
        "price_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("order_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scraped_price", sa.Float(), nullable=False),
        sa.Column("original_paid_price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("snapshot_source", snapshot_source, nullable=False),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Efficient time-series queries per item (most recent first)
    op.create_index(
        "ix_price_snapshots_order_item_scraped_at",
        "price_snapshots",
        ["order_item_id", sa.text("scraped_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_price_snapshots_order_item_scraped_at", table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.execute(sa.text("DROP TYPE IF EXISTS snapshotsource"))
