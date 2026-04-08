"""create outcome_logs table

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, UUID

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

action_taken = PgEnum(
    "price_matched", "returned_and_rebought", "ignored", "pending",
    name="actiontaken",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE actiontaken AS ENUM (
                'price_matched', 'returned_and_rebought', 'ignored', 'pending'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    op.create_table(
        "outcome_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            UUID(as_uuid=True),
            sa.ForeignKey("alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "order_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("order_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action_taken", action_taken, nullable=False),
        sa.Column("recovered_value", sa.Float(), nullable=True),
        sa.Column("was_successful", sa.Boolean(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_outcome_logs_user_id", "outcome_logs", ["user_id"])
    op.create_index("ix_outcome_logs_alert_id", "outcome_logs", ["alert_id"])


def downgrade() -> None:
    op.drop_index("ix_outcome_logs_alert_id", table_name="outcome_logs")
    op.drop_index("ix_outcome_logs_user_id", table_name="outcome_logs")
    op.drop_table("outcome_logs")
    op.execute(sa.text("DROP TYPE IF EXISTS actiontaken"))
