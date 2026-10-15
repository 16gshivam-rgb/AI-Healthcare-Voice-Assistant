"""Align indexes and remove duplicate password reset token uniqueness."""

from alembic import op

revision = "0009_align_metadata_indexes"
down_revision = "0008_admin_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_appointments_hospital_id", "appointments", ["hospital_id"])
    op.drop_constraint(
        "password_reset_tokens_token_hash_key",
        "password_reset_tokens",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "password_reset_tokens_token_hash_key",
        "password_reset_tokens",
        ["token_hash"],
    )
    op.drop_index("ix_appointments_hospital_id", table_name="appointments")
