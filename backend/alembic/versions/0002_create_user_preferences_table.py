"""create user_preferences table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, ENUM as PgEnum, UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: we manage creation/deletion manually via raw SQL below
message_tone = PgEnum("polite", "firm", "concise", name="messagetone", create_type=False)


def upgrade() -> None:
    # Idempotent enum creation — no IF NOT EXISTS in Postgres TYPE, so use DO block
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE messagetone AS ENUM ('polite', 'firm', 'concise');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    op.create_table(
        "user_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "min_savings_threshold",
            sa.Float(),
            nullable=False,
            server_default="10.0",
        ),
        sa.Column(
            "notify_price_drop",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "notify_delivery_anomaly",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "push_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "preferred_message_tone",
            message_tone,
            nullable=False,
            server_default="polite",
        ),
        sa.Column(
            "monitored_retailers",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
    op.execute(sa.text("DROP TYPE IF EXISTS messagetone"))
