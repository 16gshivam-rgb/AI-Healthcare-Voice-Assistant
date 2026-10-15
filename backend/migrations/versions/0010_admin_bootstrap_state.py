"""Add atomic first-administrator bootstrap state."""

from alembic import op
import sqlalchemy as sa

revision = "0010_admin_bootstrap_state"
down_revision = "0009_align_metadata_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_bootstrap_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "INSERT INTO admin_bootstrap_state (id, completed) "
            "SELECT 1, CASE WHEN EXISTS (SELECT 1 FROM users WHERE role = 'platform_admin') "
            "THEN TRUE ELSE FALSE END"
        )
    )


def downgrade() -> None:
    op.drop_table("admin_bootstrap_state")
