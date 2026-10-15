"""Persist payment failure details and idempotent webhook receipts."""

from alembic import op
import sqlalchemy as sa

revision = "0007_payment_webhook_idempotency"
down_revision = "0006_transactional_appointments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("failure_code", sa.String(80), nullable=True))
    op.add_column("payments", sa.Column("failure_description", sa.Text(), nullable=True))
    op.add_column(
        "payments",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_event_id", sa.String(100), nullable=False, unique=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_webhook_events_payment_id", "payment_webhook_events", ["payment_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_payment_id", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
    op.drop_column("payments", "updated_at")
    op.drop_column("payments", "failure_description")
    op.drop_column("payments", "failure_code")
